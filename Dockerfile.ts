FROM node:20-alpine AS base
WORKDIR /app

COPY package.json ./
RUN npm install -g pnpm && pnpm install

COPY . .

RUN pnpm build

EXPOSE 3000
CMD ["pnpm", "start"]