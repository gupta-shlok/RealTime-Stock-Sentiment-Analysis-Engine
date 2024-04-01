// api.js
import axios from 'axios';

export const getStockData = () => {
    let url = "https://pcg7asbzqd.execute-api.us-east-1.amazonaws.com/prod/stock-price";

    return axios.get(url)
        .then((response) => {
            console.log(response.data);
            return response.data;
        })
        .catch((error) => {
            console.error(error);
            throw new Error('Something went wrong');
        });
}
