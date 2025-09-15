import json
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from src.config.logger_config import logger


class MovieParser:
    def __init__(self):
        self.movies = []
    
    def parse_html_file(self, html_file_path: str) -> List[Dict]:
        """
        解析HTML文件，提取所有电影信息
        
        Args:
            html_file_path: HTML文件路径
            
        Returns:
            包含电影信息的字典列表
        """
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            return self.parse_html_content(html_content)
        
        except Exception as e:
            logger.error(f"解析HTML文件失败: {e}")
            return []
    
    def parse_html_content(self, html_content: str) -> List[Dict]:
        """
        解析HTML内容，提取所有电影信息
        
        Args:
            html_content: HTML内容字符串
            
        Returns:
            包含电影信息的字典列表
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            movies = []
            
            # 查找所有电影项目
            movie_items = soup.find_all('dd')
            
            for item in movie_items:
                movie_info = self._extract_movie_info(item)
                if movie_info:
                    movies.append(movie_info)
            
            logger.info(f"成功解析 {len(movies)} 部电影信息")
            return movies
        
        except Exception as e:
            logger.error(f"解析HTML内容失败: {e}")
            return []
    
    def _extract_movie_info(self, item) -> Optional[Dict]:
        """
        从单个电影项目中提取信息
        
        Args:
            item: BeautifulSoup节点对象
            
        Returns:
            电影信息字典，如果提取失败返回None
        """
        try:
            movie_info = {}
            
            # 获取电影ID和链接
            movie_link = item.find('a', href=re.compile(r'/films/\d+'))
            if not movie_link:
                return None
            
            href = movie_link.get('href')
            movie_id_match = re.search(r'/films/(\d+)', href)
            if movie_id_match:
                movie_info['id'] = int(movie_id_match.group(1))
                movie_info['url'] = f"https://www.maoyan.com{href}"
            else:
                return None
            
            # 获取电影标题
            title_element = item.find('div', class_='movie-item-title')
            if title_element and title_element.find('a'):
                movie_info['title'] = title_element.find('a').text.strip()
            else:
                # 尝试从hover信息中获取标题
                hover_title = item.find('div', class_='movie-hover-title')
                if hover_title and hover_title.find('span', class_='name'):
                    movie_info['title'] = hover_title.find('span', class_='name').text.strip()
                else:
                    return None
            
            # 获取评分
            score_info = self._extract_score(item)
            movie_info.update(score_info)
            
            # 获取详细信息（类型、主演、上映时间）
            details = self._extract_movie_details(item)
            movie_info.update(details)
            
            # 获取海报图片
            poster_info = self._extract_poster(item)
            movie_info.update(poster_info)
            
            return movie_info
        
        except Exception as e:
            logger.debug(f"提取单个电影信息失败: {e}")
            return None
    
    def _extract_score(self, item) -> Dict:
        """提取评分信息"""
        score_info = {
            'score': None,
            'score_integer': None,
            'score_fraction': None
        }
        
        try:
            # 查找评分容器
            score_container = item.find('span', class_='score')
            if score_container:
                integer_elem = score_container.find('i', class_='integer')
                fraction_elem = score_container.find('i', class_='fraction')
                
                if integer_elem and fraction_elem:
                    integer_part = integer_elem.text.strip().rstrip('.')
                    fraction_part = fraction_elem.text.strip()
                    
                    score_info['score_integer'] = integer_part
                    score_info['score_fraction'] = fraction_part
                    score_info['score'] = f"{integer_part}.{fraction_part}"
            else:
                # 尝试从其他位置获取评分
                score_elem = item.find('div', class_='channel-detail-orange')
                if score_elem:
                    integer_elem = score_elem.find('i', class_='integer')
                    fraction_elem = score_elem.find('i', class_='fraction')
                    
                    if integer_elem and fraction_elem:
                        integer_part = integer_elem.text.strip().rstrip('.')
                        fraction_part = fraction_elem.text.strip()
                        
                        score_info['score_integer'] = integer_part
                        score_info['score_fraction'] = fraction_part
                        score_info['score'] = f"{integer_part}.{fraction_part}"
        
        except Exception as e:
            logger.debug(f"提取评分失败: {e}")
        
        return score_info
    
    def _extract_movie_details(self, item) -> Dict:
        """提取电影详细信息（类型、主演、上映时间）"""
        details = {
            'genres': None,
            'actors': None,
            'release_date': None
        }
        
        try:
            # 查找详细信息容器
            hover_info = item.find('div', class_='movie-hover-info')
            if not hover_info:
                return details
            
            # 获取所有hover-title元素
            hover_titles = hover_info.find_all('div', class_='movie-hover-title')
            
            for title_elem in hover_titles:
                hover_tag = title_elem.find('span', class_='hover-tag')
                if not hover_tag:
                    continue
                
                tag_text = hover_tag.text.strip()
                
                if '类型:' in tag_text:
                    # 提取类型信息
                    genres_text = title_elem.get_text().replace('类型:', '').strip()
                    details['genres'] = genres_text
                elif '主演:' in tag_text:
                    # 提取主演信息
                    actors_text = title_elem.get_text().replace('主演:', '').strip()
                    details['actors'] = actors_text
                elif '上映时间:' in tag_text:
                    # 提取上映时间
                    release_text = title_elem.get_text().replace('上映时间:', '').strip()
                    details['release_date'] = release_text
        
        except Exception as e:
            logger.debug(f"提取电影详情失败: {e}")
        
        return details
    
    def _extract_poster(self, item) -> Dict:
        """提取海报信息"""
        poster_info = {
            'poster_url': None,
            'poster_hover_url': None
        }
        
        try:
            # 获取主海报
            poster_container = item.find('div', class_='movie-poster')
            if poster_container:
                img_elem = poster_container.find('img', {'data-src': True})
                if img_elem:
                    poster_info['poster_url'] = img_elem.get('data-src')
            
            # 获取悬停海报
            hover_img = item.find('img', class_='movie-hover-img')
            if hover_img:
                poster_info['poster_hover_url'] = hover_img.get('src')
        
        except Exception as e:
            logger.debug(f"提取海报信息失败: {e}")
        
        return poster_info
    
    def save_to_json(self, movies: List[Dict], output_file: str) -> bool:
        """
        将电影数据保存为JSON文件
        
        Args:
            movies: 电影信息列表
            output_file: 输出文件路径
            
        Returns:
            是否保存成功
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(movies, f, ensure_ascii=False, indent=2)
            
            logger.info(f"电影数据已保存到 {output_file}, 共 {len(movies)} 部电影")
            return True
        
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
            return False


# 创建全局parser实例
parser = MovieParser()