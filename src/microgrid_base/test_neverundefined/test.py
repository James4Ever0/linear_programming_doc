import sys
sys.path.append("../")
import jinja_utils
render_params = dict()
jinja_utils.load_render_and_format("template.j2", "output.txt", render_params = render_params, banner = "test_neverundefined", needFormat=False)