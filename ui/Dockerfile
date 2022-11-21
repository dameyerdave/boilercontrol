FROM node:18

RUN mkdir -p /app

WORKDIR /app

RUN npm install -g npm@latest
RUN yarn global add @quasar/cli

ENTRYPOINT [ "./entrypoint.sh" ]