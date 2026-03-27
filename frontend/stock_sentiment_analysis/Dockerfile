# build environment
FROM node:18-alpine as build
WORKDIR /app
COPY package.json package-lock.json ./

RUN npm install

COPY . ./
RUN npm run build

# production environment
FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
# Copy custom nginx config if we need to route API requests, but we'll rely on REACT_APP_API_URL instead
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
