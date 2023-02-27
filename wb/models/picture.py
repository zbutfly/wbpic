from wb.models import Weibo, CONSTANTS
from wb.context import opts

minw = opts.get('min_dimension', 360)
minh = opts.get('min_dimension', 360)


class Picture(Weibo):

	@classmethod
	def notsmall():
		return lambda w, h: w < minw or h <= minh or w + h < 1600

	def __init__(self, json: dict) -> None:
		super().__init__()

	def parse(self, mblog):
		pass