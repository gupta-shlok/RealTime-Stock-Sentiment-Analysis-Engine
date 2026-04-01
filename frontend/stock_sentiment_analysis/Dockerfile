# build environment
FROM node:18-alpine as build
WORKDIR /app
COPY package.json package-lock.json ./

RUN npm install

COPY . ./

# Pass build-time environment variables for Create React App
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=${REACT_APP_API_URL}

RUN npm run build

# production environment
FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
