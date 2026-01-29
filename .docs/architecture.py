from diagrams import Cluster, Diagram
from diagrams.custom import Custom
from diagrams.onprem.client import User
from diagrams.onprem.compute import Server
from diagrams.onprem.monitoring import Prometheus
from diagrams.programming.language import Python

with Diagram("Architecture", show=False, filename="architecture"):
    user = User("User")
    dashboard = Custom("Textual Dashboard", "dashboard_icon.png")
    sensor = Custom("Meat Probe", "probe_icon.png")

    with Cluster("Service"):
        http_server = Server("HTTP Server")
        background_task = Python("BLE Monitor Task")
        metrics_collector = Prometheus("Metrics Collector")

    with Cluster("Prometheus"):
        scraper = Prometheus("Scraper")
        database = Prometheus("Database")

    user >> dashboard
    dashboard >> database
    scraper >> http_server
    scraper >> database
    background_task >> sensor
    background_task >> metrics_collector
    http_server >> metrics_collector
