sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
git clone -b jp https://github.com/huwenjun1-ola/Akagi
cp Akagi/mjai_bot/mortal/libriichi/libriichi-3.12-x86_64-unknown-linux-gnu.so Akagi/mjai_bot/mortal/libriichi.so
python -m pip install -r Akagi/requirements.txt