"""Exercise the real Windows agent against a local mock Hub."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import tempfile
from websockets.asyncio.server import serve


async def smoke(executable: Path, target: str):
    expected_arch = target.split('-')[0]
    done = asyncio.get_running_loop().create_future()
    connections, boot_id = 0, None

    async def tcp_probe(reader, writer):
        writer.close()
        await writer.wait_closed()

    async with await asyncio.start_server(tcp_probe, '127.0.0.1', 0) as tcp_server:
        probe_port = tcp_server.sockets[0].getsockname()[1]

        async def hub(ws):
            nonlocal connections, boot_id
            connections += 1
            generation = connections
            try:
                assert ws.request.path == '/api/agent/ws', ws.request.path
                assert ws.request.headers['Authorization'] == 'Bearer smoke-test-token'
                first = json.loads(await ws.recv())
                assert first['jsonrpc'] == '2.0' and first['method'] == 'hello', first
                facts = first['params']
                assert facts['os'] == 'Windows' and facts['arch'] == expected_arch, facts
                assert facts['cpu_cores'] >= 1 and facts['mem_total'] > 0, facts
                assert facts['disk_total'] > 0 and facts['agent_version'], facts
                await ws.send(json.dumps({
                    'jsonrpc': '2.0', 'method': 'ping.tasks',
                    'params': [{'id': 7, 'target': f'127.0.0.1:{probe_port}', 'interval': 5}],
                }))
                reports, ping_ok = 0, False
                async for raw in ws:
                    message = json.loads(raw)
                    params = message['params']
                    if message['method'] == 'ping.result':
                        assert params['task_id'] == 7 and params['latency_ms'] >= 0, params
                        ping_ok = True
                    elif message['method'] == 'report':
                        assert 0 <= params['cpu'] <= 100 and len(params['load']) == 3, params
                        assert 0 <= params['mem_used'] <= params['mem_total'], params
                        assert 0 <= params['disk_used'] <= params['disk_total'], params
                        for field in ('net_rx', 'net_tx', 'net_rx_total', 'net_tx_total', 'uptime'):
                            assert isinstance(params[field], int) and params[field] >= 0, (field, params)
                        assert params['boot_id'] and 'iface' in params, params
                        if boot_id is None:
                            boot_id = params['boot_id']
                        assert params['boot_id'] == boot_id, 'Boot ID changed without a reboot'
                        reports += 1
                    if reports >= 2 and ping_ok:
                        if generation == 1:
                            await ws.close(code=1012, reason='Simulated Hub restart')
                        elif not done.done():
                            done.set_result(True)
                        break
            except Exception as error:
                if not done.done():
                    done.set_exception(error)

        async with serve(hub, '127.0.0.1', 0) as server:
            port = server.sockets[0].getsockname()[1]
            with tempfile.TemporaryDirectory(prefix='monitor-agent-smoke-') as tmp:
                log_path = Path(tmp) / 'agent.log'
                env = dict(os.environ, ProgramData=tmp)
                with log_path.open('wb') as log:
                    process = await asyncio.create_subprocess_exec(
                        str(executable.resolve()), '--server', f'http://127.0.0.1:{port}',
                        '--token', 'smoke-test-token', env=env,
                        stdout=log, stderr=asyncio.subprocess.STDOUT,
                    )
                    try:
                        await asyncio.wait_for(done, timeout=40)
                        assert connections >= 2
                    except BaseException:
                        print(log_path.read_text(errors='replace'))
                        raise
                    finally:
                        if process.returncode is None:
                            process.terminate()
                        try:
                            await asyncio.wait_for(process.wait(), timeout=5)
                        except TimeoutError:
                            process.kill()
                            await process.wait()
    print(f'PASS: {expected_arch} metrics, TCP probes, and reconnect')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    parser.add_argument('--arch', required=True)
    args = parser.parse_args()
    asyncio.run(smoke(args.executable, args.arch))
