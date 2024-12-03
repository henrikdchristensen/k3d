

from kubernetes import client, config, utils

config.load_kube_config()
v1 = client.CoreV1Api()
active_challenges = v1.list_namespaced_pod(namespace='project', label_selector=f'type=ctf,username=nytest1').items
active_challenges_labels = [challenge.metadata.labels for challenge in active_challenges]

print(active_challenges_labels)