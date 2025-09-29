1. 爬取全部电影: 包括正在热映与即将上映
2. 补充详情: 之前得到的电影是从列表页面中取得的, 因此要根据 id 继续逐个取得进一步的信息, 如电影导演, 国家等
3. 筛选我喜欢的电影: 根据是否过滤大陆 & 首映年份在 xx 年之前进行筛选
4. 得到电影对应的放映日期列表: 对筛选后的电影, 查看其所有的放映日期列表 selected_movie_showdate_list_scraper
5. 得到电影对应的影院列表: 根据电影与放映日期, 逐个得到所有有排片的影院 selected_movie_cinema_list_scraper
6. 得到电影对应的排片列表: 根据电影与影院, 直接得到全部排片 selected_movie_showtime_scraper