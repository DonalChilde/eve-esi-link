### Caching

eve-link caches GET requests, so the same request may return cached data if it has not expired. This can be a huge time saver, and can simplify data retrieval strategies. The cache could be treated just like a database (it is) and requests can be made as often as desired. Network calls will only be made if the data has not been cached, or the cache is stale.

TODO: describe cache key criteria