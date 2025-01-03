<div align="center">

# 🚨 Vigil

Real-Time Traffic Accident Detection System

</div>

## 📊 Project Overview

Vigil is a traffic accident detection system that uses computer vision and machine learning to analyze live traffic camera feeds. The core idea is to build a system that extract video frames from a large number of traffic cameras, runs it through a computer vision model that detects car accidents and then notify a user interface.
Follow along the journey of building this project in my newsletter [Calculated Randonmess](https://calculatedrandomness.substack.com/).

![](https://github.com/user-attachments/assets/aa4770bd-0493-4247-b8f5-775777211e1f)


## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- UV package installer

### 🔧 Installation

**1. Clone the repository**
```bash
git clone https://github.com/joaoflf/vigil.git
cd vigil
```

**2. Configure Environment**

Create `secrets` directory for your docker secrets and write your own secrets inside each file
```secrets/*
grafana-admin-user
grafana-admin-password
influxdb2-admin-username
influxdb2-admin-password
influxdb2-admin-token
```

Create a `.env` file in the root directory:
```env
RF_API_KEY = <your_roboflow_api_key>
INFLUX_ORG = <your_influxdb_token>
INFLUX_HOST = http://localhost:8086
INFLUX_TOKEN = <your_influxdb_token>
```
[how to get a Roboflow API key](https://inference.roboflow.com/quickstart/configure_api_key/)



**3. Install Dependencies**

Set up virtual environment and install dependencies:
```bash
uv venv --python 3.11.0
uv sync
```

**4. Launch Services**
```bash
docker-compose up -d
```

**5. Start Vigil**
```bash
uv run scripts/start.py
```

## 📊 Grafana Dashboard Setup

1. Open your browser and navigate to `http://localhost:3000`

2. Log in with the credentials you set in docker secrets

3. Import the dashboard:
   - Go to Dashboards → Import
   - Select the JSON file from `grafana-dashboards` folder
   - Click "Load"

## 🏗️ Project Structure

```
vigil/
├── src/               # Source code
├── scripts/           # Utility scripts
├── tests/             # Test files
├── grafana-dashboards/# Grafana dashboard templates
└── docker-compose.yml # Docker services configuration
```



## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


---
<div align="center">
Made with ❤️ by João Fernandes
</div>
