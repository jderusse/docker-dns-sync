#!/usr/bin/env python

import os
import sys
import argparse
import pyinotify
from docker import Client
from docker.errors import APIError

parser = argparse.ArgumentParser(description='Synchronise resolv.conf between the host and a container.')
parser.add_argument('container', help='id or name of the container')
parser.add_argument('--watch', action='store_true', help='watch the file system for changes')
parser.add_argument('--dns', help='Dns to sets in the hosts')

args = parser.parse_args()

container_name = args.container
watch = args.watch

docker_client = Client()


def find_container(container_name):
    try:
        return docker_client.inspect_container(container_name)
    except APIError:
        pass

    for c in docker_client.containers():
        if container_name in c['Labels'].keys():
            return c

    return None


def get_excluded_addresses(containerId):
    container_data = docker_client.inspect_container(containerId)

    return [
        '127.0.0.1',
        str(container_data['NetworkSettings']['IPAddress']),
        str(container_data['NetworkSettings']['Gateway']),
    ]


def get_target_path(path):
    target = '/data/dns'

    full_path = target + path
    if os.path.exists(full_path):
        return full_path

    if os.path.islink(full_path):
        return get_target_path(os.readlink(full_path))

    if path == '/' or not path:
        return None

    sub = get_target_path(os.path.dirname(path))
    if sub is None:
        return None

    return os.path.join(sub, os.path.basename(path))


def is_nameserver_excluded(nameserver, excluded_addresses):
    for address in excluded_addresses:
        if address in nameserver:
            return True

    return False


def replace_resolvconf(resolvconf, containerId):
    current_resolvconf = docker_client.execute(containerId, 'cat /etc/resolv.conf')
    if current_resolvconf != resolvconf:
        docker_client.execute(containerId, 'sh -c "echo > /etc/resolv.conf"')
        for line in resolvconf.splitlines():
            docker_client.execute(containerId, 'sh -c "echo \\\"%s\\\" >> /etc/resolv.conf"' % line.replace('"', '\\\\\\\"'))


def get_new_resolvconf(containerId):
    real_path = get_target_path('/etc/resolv.conf')
    if not os.path.exists(real_path):
        sys.exit(1)

    excluded_addresses = get_excluded_addresses(containerId)
    with open(real_path, 'r') as f:
        return "\n".join([x.strip() for x in f if not is_nameserver_excluded(x, excluded_addresses)])


def inject_dns(dns):
    print('Inject dns')
    real_path = get_target_path('/etc/resolv.conf')
    if not os.path.exists(real_path):
        sys.exit(1)

    with open(real_path, 'r') as f:
        resolvconf = "\n".join([x.strip() for x in f])

    if dns in resolvconf:
        return

    with open(real_path, 'w') as f:
        f.write('nameserver %s\n' % dns)
        f.write(resolvconf + "\n")


def sync():
    print('Synchronizing')
    if args.dns:
        inject_dns(args.dns)

    container = find_container(container_name)['Id']
    if container is not None:
        replace_resolvconf(get_new_resolvconf(container).strip(), container)


sync()


class ModHandler(pyinotify.ProcessEvent):
    def process_default(self, event):
        if event.pathname.endswith('resolv.conf'):
            sync()

if watch:
    wm = pyinotify.WatchManager()
    notifier = pyinotify.Notifier(wm, ModHandler(), timeout=1000)
    files = [
        '/data/dns/etc/resolv.conf',
        '/data/dns/etc/',
        get_target_path('/etc/resolv.conf'),
        os.path.dirname(get_target_path('/etc/resolv.conf')),
    ]

    files = [x for x in files if os.path.exists(x)]
    wm.add_watch(files, pyinotify.IN_MOVED_TO | pyinotify.IN_CREATE | pyinotify.IN_MOVE_SELF | pyinotify.IN_MODIFY | pyinotify.IN_CLOSE_WRITE, rec=False)
    notifier.loop()
