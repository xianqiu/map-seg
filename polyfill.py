import math

from shapely.geometry import Polygon, MultiPolygon, Point
import matplotlib.pyplot as plt


class PolyGetter(object):
    """ 生成正多边形对象
    """

    def __init__(self, radius, k, theta=0):
        """ 生成正k边形（的顶点）
        """
        self.radius = radius  # 半径
        self.k = k  # 正多边形的边数
        self.theta = theta  # 起始角度: degree

    def from_center(self, center):
        """ 输入中心点的坐标，返回对应的正多边形
        :param center: Point对象
        """

        def get_xy(i):
            x = center.x + self.radius * math.cos(2 * math.pi * (i / self.k + self.theta / 360))
            y = center.y + self.radius * math.sin(2 * math.pi * (i / self.k + self.theta / 360))
            return x, y

        return Polygon([Point(get_xy(i)) for i in range(self.k)])

    def from_vertex(self, vertex, i):
        """ 给定顶点，返回对应的正k边形
        :param vertex: 顶点坐标，Point对象
        :param i: 顶点的编号（按极坐标顺序编号）
        """
        c_x = vertex.x - self.radius * math.cos(2 * math.pi * i / self.k + self.theta)
        c_y = vertex.y - self.radius * math.sin(2 * math.pi * i / self.k + self.theta)
        return self.from_center(Point(c_x, c_y))

    def neighbors_of(self, poly):
        """ 输入正多边形，返回它所有邻接的多边形
        :param poly: 多边形，Polygon对象
        """
        dist = self.radius * math.cos(math.pi / self.k)  # 计算中心到边的距离
        p = PolyGetter(2 * dist,
                       self.k,
                       self.theta + 180 / self.k)
        centers = list(p.from_center(poly.centroid).exterior.coords)
        return [Polygon(self.from_center(Point(c))) for c in centers]


class PolyFill(object):
    """ 给定一个多边形区域, 用正多边形填充它.
    """

    def __init__(self, boundary, center):
        """
        :param boundary: 被分割的多边形, Polygon对象 或 顶点坐标[(x0,y0), (x1, y1), ...]
        :param center: 锚点，以center为出发点进行分割, Point对象
        """
        self._boundary = boundary
        if not isinstance(self._boundary, Polygon):
            self._boundary = Polygon(self._boundary)
        self._center = center
        self._radius = None
        self._k = None
        self._theta = None
        self._poly_getter = None
        self._res_polys = []  # 填充结果（保存为多边形对象）
        self._result = []  # 计算结果（保存为多边形的顶点坐标集合）
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

    def get_result(self):
        return self._result

    def show(self):
        plt.plot(self._center.x, self._center.y, 'x')
        for points in self._result:
            plt.plot(*list(zip(*points)))
        plt.axis('equal')
        plt.show()

    def fill(self):
        """
        :return:
        [[(x11, y11), (x12, y12) ...]  # 多边形1
         [(x21, y21), (x22, y22) ...]  # 多边形2
         ...]                          # ...
        """
        assert self._radius, ValueError("set parameters first!")

        start_poly = self._poly_getter.from_center(self._center)
        # 以start_poly为起点执行BFS填充boundary
        self._fill_by_bfs(start_poly)
        self._result = [list(poly.exterior.coords) for poly in self._res_polys]
        return self

    def _fill_by_bfs(self, start_poly):
        """ 给定初始的填充多边形, 按照BFS的方式填充周围的区域
        以k多边形为例(k=3,4,6), 有k个多边形与它相邻.
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
            self._res_polys.append(s)
        # MultiPolygon对象则依次把它包含的Polygon对象保存
        elif isinstance(s, MultiPolygon):
            for p in s:
                self._res_polys.append(p)

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


if __name__ == '__main__':

    def generate_boundary():
        # 生成一个半径为10的正四边形。
        return PolyGetter(radius=10, k=4, theta=0).from_center(Point(0, 0))

    pf = PolyFill(generate_boundary(), center=Point(0, 0))
    pf.set_params(radius=2, k=6)  # 用半径为2的正六边形填充
    pf.fill().show()

