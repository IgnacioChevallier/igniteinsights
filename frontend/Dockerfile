# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,id=s/0346e379-5a0a-4dea-b002-bc871b206fce-/root/.npm,target=/root/.npm npm ci

FROM deps AS development
ENV NODE_ENV=development
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG API_BASE_URL=http://api:8000
ENV API_BASE_URL=$API_BASE_URL
# Better Auth is imported while Next collects route metadata. These non-production values exist
# only in the builder stage; the runner receives its real URL and secret at runtime.
ENV BETTER_AUTH_URL=http://build.invalid
ENV BETTER_AUTH_SECRET=build-only-secret-never-used-at-runtime
RUN --mount=type=cache,id=s/0346e379-5a0a-4dea-b002-bc871b206fce-/app/.next/cache,target=/app/.next/cache npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public* ./public/
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
