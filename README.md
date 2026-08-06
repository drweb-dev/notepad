# notepad
custom

# 主机服务
+ https://www.racknerd.com/

# 域名查询
+ https://www.virustotal.com/gui/home/search
+ https://ip.thc.org/
+ https://crt.sh/  
+ https://rapiddns.io/
+ https://otx.alienvault.com/
+ 
# AI 工具
+ https://duck.ai/
+ https://www.google.com/search?udm=50&aep=11
+ https://platform.deepseek.com/sign_in

# Ubuntu 24.04 LTS install CyberStrikeAI
```
sudo rm /var/lib/dpkg/lock-frontend
sudo rm /var/lib/dpkg/lock
sudo dpkg --configure -a
sudo apt update
apt install -y unzip net-tools tree build-essential python3.12-venv nmap masscan sqlmap nikto gobuster hydra hashcat john binwalk
wget https://go.dev/dl/go1.26.5.linux-amd64.tar.gz
sudo rm -rf /usr/local/go && sudo tar -C /usr/local -xzf go1.26.5.linux-amd64.tar.gz
cat << 'EOF' >> ~/.profile
# Golang Env Configuration
export GOROOT=/usr/local/go
export GOPATH=$HOME/go
export PATH=$GOPATH/bin:$GOROOT/bin:$PATH
EOF
source ~/.profile
git clone https://github.com/Ed1s0nZ/CyberStrikeAI.git
cd CyberStrikeAI
chmod +x run.sh && CGO_ENABLED=1 ./run.sh
```
