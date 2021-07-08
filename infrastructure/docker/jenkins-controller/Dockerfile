FROM jenkins/jenkins:2.289.2-lts

# Install custom plugins
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN /usr/local/bin/install-plugins.sh < /usr/share/jenkins/ref/plugins.txt

COPY modify_casc.py /modify_casc.py
COPY jenkins.j2 /jenkins.j2

USER root

RUN apt-get update &&\
    apt-get install -y python-pip &&\
    pip install jinja2 dnspython &&\
    rm -rf /var/lib/apt/lists/* &&\
    touch /jenkins.yaml &&\
    chown jenkins: /jenkins.yaml &&\
    sed -i '/\/bin\/bash*/a \\n\/modify_casc.py' /usr/local/bin/jenkins.sh

# User back to jenkins
USER jenkins