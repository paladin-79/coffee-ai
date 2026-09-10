# Coffee AI Challenge — frontend
# S1 runs the Next.js dev server in the container: simplest thing that gives a
# playable slice. A production `next build` image is an S5 (event hardening) task.
FROM node:20-alpine

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]
