from jinja2 import Environment, FileSystemLoader, StrictUndefined

# Create Jinja2 environment with the extension
env = Environment(
    loader=FileSystemLoader('.'),
    undefined=StrictUndefined,
    extensions=['jinja2.ext.do']
)

# Render the template
template = env.get_template('template.j2')
rendered = template.render(name='John Doe')

# Print the rendered output
print(rendered)
