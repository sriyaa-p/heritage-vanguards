# Stage 1: Build
FROM node:18-alpine AS builder
WORKDIR /app

# Install ALL dependencies including devDependencies
# (tailwindcss, postcss, autoprefixer, typescript are devDependencies)
ENV NODE_ENV=development
COPY package*.json ./
RUN npm install

# Copy source and config files, then build the production bundle
COPY . .
ENV NODE_ENV=production
RUN npm run build

# Remove devDependencies so the runner image stays lean
RUN npm prune --omit=dev

# Stage 2: Production runner
FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copy build output, production node_modules, and runtime config
COPY --from=builder /app/.next /app/.next
COPY --from=builder /app/public /app/public
COPY --from=builder /app/node_modules /app/node_modules
COPY --from=builder /app/package.json /app/package.json
COPY --from=builder /app/next.config.js /app/next.config.js
COPY --from=builder /app/postcss.config.js /app/postcss.config.js
COPY --from=builder /app/tailwind.config.js /app/tailwind.config.js

EXPOSE 3000
CMD ["npm", "start"]