IMAGE=cs2-bot
TAG=latest
SERVER=erik@165.227.148.29
SERVER_DIR=/home/erik/cs2-bot

.PHONY: test build upload deploy clean

test:
	python -m py_compile player_finder.py

build:
	IMG=$(IMAGE) TAG=$(TAG) docker compose -f docker/build.yml build

upload:
	rsync -av --exclude '.git' --exclude '__pycache__' ./ $(SERVER):$(SERVER_DIR)

deploy: build upload
	ssh $(SERVER) "cd $(SERVER_DIR) && IMG=$(IMAGE) TAG=$(TAG) BOT_TOKEN=$(BOT_TOKEN) docker stack deploy -c docker/run.yml cs2bot"

clean:
	docker system prune -f
