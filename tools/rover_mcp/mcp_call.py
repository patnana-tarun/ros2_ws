#!/usr/bin/env python3
"""Drive the rover MCP server from a shell (testing, or when the client has not loaded it yet).

    mcp_call.py 'tool_name {"arg": 1}' ['tool2 {...}' ...]

Starts run.sh over stdio like Claude Code does, calls the tools in order in ONE server session (so a
sim started by the first call is still there for the next), prints text results and saves images
next to this script in runs/mcp_call_images/.
"""
import asyncio
import base64
import json
import os
import sys
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = os.path.dirname(os.path.abspath(__file__))


async def main(calls):
    params = StdioServerParameters(command=os.path.join(HERE, 'run.sh'), args=[], env=dict(os.environ))
    img_dir = os.path.join(HERE, 'runs', 'mcp_call_images')
    os.makedirs(img_dir, exist_ok=True)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            for c in calls:
                name, _, arg = c.partition(' ')
                if name == 'tools':
                    t = await s.list_tools()
                    print('\n'.join(f'- {x.name}' for x in t.tools))
                    continue
                if name == 'sleep':
                    await asyncio.sleep(float(arg))
                    continue
                t0 = time.time()
                res = await s.call_tool(name, json.loads(arg) if arg.strip() else {})
                print(f'===== {name} ({time.time() - t0:.1f}s) error={res.isError}')
                for k, item in enumerate(res.content):
                    if item.type == 'text':
                        print(item.text)
                    elif item.type == 'image':
                        p = os.path.join(img_dir, f'{time.strftime("%H%M%S")}_{name}_{k}.'
                                         + item.mimeType.split('/')[-1])
                        open(p, 'wb').write(base64.b64decode(item.data))
                        print(f'[image saved: {p}]')
                sys.stdout.flush()


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1:]))
