# Docker DNS-sync

dns-sync sets up a container watching host's /etc/resolv.conf and updates
others container's one.

## Usage

    $ docker run -d --name dns-sync \
        --restart always \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v /etc/:/data/dns/etc \
        -v /run:/data/dns/run \
        jderusse/dns-sync CONTAINER_ID

## Options

* --wath: Watch host's resolv.conf and syncronize container's one
* --dns ServerName: When sets, update the hosts resolv.conf to add the given
    serverName
