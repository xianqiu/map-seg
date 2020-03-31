from shapely.geometry import Polygon, MultiPolygon

from poly_getter import PolyGetter


class PolyFill(object):
    """ 给定一个多边形区域, 用正多边形填充它.
    """

    def __init__(self, boundary, center):
        """
        :param boundary: 被分割的多边形, Polygon对象
        :param center: 锚点，以center为出发点进行分割, Point对象
        """
        self._boundary = boundary
        self._center = center
        self._radius = None
        self._k = None
        self._theta = None
        self._poly_getter = None
        self._result = []
        # 用来保存已经搜索过的正多边形（用中心点来表示）
        self._searched_polys = set({})

    def set_params(self, radius, k=6, theta=0):
        """ 参数设置.
        :param radius: 正多边形外接圆的半径
        :param k: 正k多边形.  k = 3, 4, 6
        :param theta: 正多边形的起始角度（度数）
        """
        self._radius = radius
        self._k = k
        self._theta = theta
        assert radius > 0 and k in {3, 4, 6}, \
            ValueError('radius > 0 and k in (3, 4, 6)')
        self._radius = radius
        self._k = k
        self._theta = theta
        self._poly_getter = PolyGetter(self._radius, self._k, self._theta)

        return self

    def run(self):
        """
        :return:
        [[(x11, y11), (x12, y12) ...]  # 多边形1
         [(x21, y21), (x22, y22) ...]  # 多边形2
         ...]                          # ...
        """
        assert self._radius, ValueError("set parameters first!")

        start_poly = self._poly_getter.from_center(self._center)
        # 以start_poly为起点执行BFS填充boundary
        self._fill(start_poly)
        return [list(poly.exterior.coords) for poly in self._result]

    def _fill(self, start_poly):
        """ 给定初始的填充多边形, 按照BFS的方式填充周围的区域.
        以k多边形为例(k=3,4,6), 有 360/k 个多边形与它相邻.
        """
        self._mark_as_searched(start_poly)
        q = [start_poly]
        while len(q):
            poly = q.pop(0)
            self._append_to_result(poly)
            # 把有效的多边形加入队列. 有效的定义:
            # 1. 与poly邻接;
            # 2. 未被搜索过;
            # 3. 在边界内（与boundary定义的区域有交集)
            q += self._get_feasible_neighbors(poly)

    def _mark_as_searched(self, poly):
        """ 把多边形标记为'已搜索'
        """
        self._searched_polys.add(self._get_poly_id(poly))

    @staticmethod
    def _get_poly_id(poly):
        """ 用多边形的中心点的位置判断两个多边形是否相同.
        注意浮点数精度问题.
        """
        c = poly.centroid
        return '%.6f,%.6f' % (c.x, c.y)

    def _is_searched(self, poly):
        """ 判断多边形是否存在
        """
        return self._get_poly_id(poly) in self._searched_polys

    def _append_to_result(self, poly):
        """ 把正多边形poly保存到结果集.
        """
        # poly与boundary取交集, 然后保存结果
        s = self._boundary.intersection(poly)
        if s.is_empty:
            return
        # Polygon对象则直接保存
        if isinstance(s, Polygon):
            self._result.append(s)
        # MultiPolygon对象则依次把它包含的Polygon对象保存
        elif isinstance(s, MultiPolygon):
            for p in s:
                self._result.append(p)

    def _get_feasible_neighbors(self, poly):
        """ 计算与poly邻接的有效的正多边形, 然后标记为'已搜索'.
        """
        def mark_searched(p):
            self._mark_as_searched(p)
            return p

        def is_feasible(p):
            if self._is_searched(p) or self._boundary.intersection(p).is_empty:
                return False
            return True

        # 1. 仅包含'未被搜索'和'不在界外'的正多边形
        # 2. 把poly所有的feasible多边形标记为'已搜索'
        return [mark_searched(p)
                for p in self._poly_getter.neighbors_of(poly)
                if is_feasible(p)]



