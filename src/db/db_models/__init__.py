from sqlalchemy.orm import declarative_base

# 所有 models 都继承这个基类, 能自动将类映射为数据库中的表
Base = declarative_base()

# 加这行的作用是: 数据库在建表的时候, 只对已经将信息注册到 Base.metadata 的类进行建表
# 而类在被导入的时候才会被定义; 并且继承自 base 的类在被定义才会注册到 Base.metadata
# 因此, 需要在建表之前导入, 进而触发定义与注册行为
from .movie import Movie  # noqa
from .cinema import Cinema  # noqa
from .movie_cinema_schedule import MovieCinemaSchedule  # noqa
