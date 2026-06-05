sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev -y
sudo apt install -y git-lfs
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
git clone -b jp https://github.com/huwenjun1-ola/Akagi2
cd Akagi && git lfs pull
cp Akagi/mjai_bot/mortal/libriichi/libriichi-3.12-x86_64-unknown-linux-gnu.so Akagi/mjai_bot/mortal/libriichi.so
cp Akagi/mjai_bot/mortal3p/libriichi/libriichi3p-3.12-x86_64-unknown-linux-gnu.so Akagi/mjai_bot/mortal3p/libriichi3p.so
python -m pip install -r Akagi/requirements.txt