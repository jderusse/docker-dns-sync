FROM python:2.7
MAINTAINER Jérémy Derussé "jeremy@derusse.com"

RUN pip install docker-py
RUN pip install pyinotify

ADD bin/update_resolv.py /opt/update_resolv.py

ENTRYPOINT ["/opt/update_resolv.py"]
CMD ["dns-gen", "--watch", "--dns", "172.17.42.1"]
