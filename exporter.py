import json
import pythonping
import requests
import prometheus_client as prom
from time import sleep


ping = prom.Summary('ping_processing_seconds', 'Time spent processing ICMP pings')
http = prom.Summary('http_processing_seconds', 'Time spent processing HTTP requests')
report = prom.Enum('node_status', 'Node statuses', ['node'], states=['up', 'down'])
times = prom.Gauge('node_latency', 'Node latencies', ['node'])
with open("config.json") as fp:
    conf = json.load(fp)
nodes = conf['nodes']


@http.time()
def http_request(node, address):
    try:
        r = requests.get(address)
        if r.status_code >= 400:
            success = 'down'
            times.labels(node).set(-1)
        else:
            success = 'up'
            times.labels(node).set(r.elapsed.microseconds/1000)
    except requests.exceptions.RequestException:
        success = 'down'
        times.labels(node).set(-1)
    report.labels(node).state(success)


@ping.time()
def icmp_request(node, address):
    try:
        r = pythonping.ping(address, count=1)
        if r.packet_loss > 0:
            success = 'down'
            times.labels(node).set(-1)
        else:
            success = 'up'
            times.labels(node).set(r.rtt_avg*1000)
    except Exception as e:
        print(e)
        success = 'down'
    report.labels(node).state(success)


if __name__ == '__main__':
    print("Starting Prometheus Reporter...")
    prom.start_http_server(conf['port'])
    while True:
        for n in nodes:
            if nodes[n]['method'] == 'http':
                print(f"[{n}] Sending HTTP to {nodes[n]['address']}")
                http_request(n, nodes[n]['address'])
            elif nodes[n]['method'] == 'ping':
                print(f"[{n}] Sending ICMP to {nodes[n]['address']}")
                icmp_request(n, nodes[n]['address'])
        sleep(conf['sleep_secs'])
