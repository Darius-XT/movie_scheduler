ARG NODE_BASE_IMAGE=public.ecr.aws/docker/library/node:20-alpine
FROM ${NODE_BASE_IMAGE}

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend /app

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
