FROM centos:8

RUN yum -y update \
    && yum -y install python3 python3-pip \
    && yum -y clean all

RUN pip3 install kafka-python sseclient

COPY stream_generator.py .

CMD ["python3","stream_generator.py"]
