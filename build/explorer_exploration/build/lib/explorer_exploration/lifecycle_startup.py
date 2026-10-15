"""
Lifecycle startup: sends STARTUP to Nav2 lifecycle managers (autostart off) after a delay.

A service client that calls as soon as it sees the server can lose its request or the reply,
because the server side has not yet matched the new client's endpoints. With ~25 processes
starting at once this happened to the managers' change_state calls (bringup hung at
"Configuring ...") and to a `ros2 service call` sent from the launch file (fresh process, the
STARTUP request never arrived). This node starts with the launch and creates its clients at
once, then waits `delay` seconds (wall time) before calling, so every endpoint has matched by
the time anything is sent. It calls once per manager and exits.
"""

import time

import rclpy
from rclpy.node import Node
from nav2_msgs.srv import ManageLifecycleNodes


def run(node):
    managers = node.declare_parameter(
        'managers', ['lifecycle_manager_slam', 'lifecycle_manager_navigation']).value
    delay = node.declare_parameter('delay', 8.0).value
    log = node.get_logger()

    clients = {m: node.create_client(ManageLifecycleNodes, f'/{m}/manage_nodes')
               for m in managers}
    time.sleep(delay)

    futures = {}
    for m, client in clients.items():
        if not client.wait_for_service(timeout_sec=30.0):
            log.error(f'{m}: manage_nodes not available, not started')
            continue
        log.info(f'{m}: STARTUP')
        futures[m] = client.call_async(
            ManageLifecycleNodes.Request(command=ManageLifecycleNodes.Request.STARTUP))

    # The reply comes when the manager has activated all its nodes.
    deadline = time.monotonic() + 60.0
    for m, future in futures.items():
        rclpy.spin_until_future_complete(
            node, future, timeout_sec=max(0.0, deadline - time.monotonic()))
        if not future.done():
            log.warn(f'{m}: no reply within 60 s (check the manager log)')
        elif future.result().success:
            log.info(f'{m}: nodes active')
        else:
            log.error(f'{m}: STARTUP failed')


def main(args=None):
    rclpy.init(args=args)
    node = Node('lifecycle_startup')
    try:
        run(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
