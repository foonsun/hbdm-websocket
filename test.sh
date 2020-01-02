source /data/pyenv/bin/activate
for i in {1..500};do
nohup python websocket_example.py > logs/$i.log 2>&1 &
done
