from flask import Flask, request, render_template_string
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import networkx as nx
import io
import base64

app = Flask(__name__)

def warshall_reachability(matrix):
    n = len(matrix)
    reach = [row[:] for row in matrix]
    for k in range(n):
        for i in range(n):
            for j in range(n):
                reach[i][j] = reach[i][j] or (reach[i][k] and reach[k][j])
    return reach

def matrix_to_graph(matrix):
    G = nx.DiGraph()
    n = len(matrix)
    for i in range(n):
        for j in range(n):
            if matrix[i][j] and i != j:
                G.add_edge(i, j)
    return G

def plot_graph(graph, paths=None):
    pos = nx.kamada_kawai_layout(graph)
    plt.figure(figsize=(9, 9))
    nx.draw_networkx_nodes(graph, pos, node_color="#E3AC61FF", node_size=400, alpha=0.9)
    nx.draw_networkx_labels(graph, pos, font_size=16, font_family='Arial')

    edge_counts = {}
    for u, v in graph.edges():
        edge_counts[(u,v)] = edge_counts.get((u,v), 0) + 1
    
    drawn_edges = {}

    # Палитра оранжевых оттенков (можно добавить линейную смену прозрачности)
    colors = list(mcolors.LinearSegmentedColormap.from_list("", ["#000000", "#FF6F00"])(np.linspace(0,1,10)))

    for u, v in graph.edges():
        count = edge_counts[(u,v)]
        index = drawn_edges.get((u,v), 0)
        if count == 1:
            rad = 0
        else:
            step = 0.6 / (count - 1) if count > 1 else 0
            rad = -0.3 + step*index
        drawn_edges[(u,v)] = index + 1

        # Выбираем цвет из палитры, основанный на индексе
        color = colors[index % len(colors)]
        alpha = 0.7 - 0.07*index  # чуть уменьшаем прозрачность

        # Толщина рёбер с уменьшением по индексу
        width = max(2 - 0.3*index, 0.8)

        nx.draw_networkx_edges(
            graph, pos, edgelist=[(u,v)],
            arrowstyle='-|>', arrowsize=12,
            width=width,
            edge_color=color,
            alpha=alpha,
            connectionstyle=f"arc3,rad={rad}"
        )
    plt.axis('off')
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=130)
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()



html_template = '''
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Транзитивное замыкание (Уоршелл)</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
<style>
  /* Основные цвета черно-оранжевой темы */
  body {
    background-color: #121212;
    color: #FFA500;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  }

  h2, h5 {
    color: #FF8C00;
  }

  .container {
    background-color: #1E1E1E;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 0 15px #FF8C0055;
  }

  textarea.form-control {
    background-color: #222;
    color: #FFA500;
    border: 1px solid #FF8C00;
    resize: vertical;
  }

  textarea.form-control::placeholder {
    color: #FFB84D;
  }

  select.form-select {
    background-color: #222;
    color: #FFA500;
    border: 1px solid #FF8C00;
  }

  select.form-select option {
    background-color: #1e1e1e;
    color: #FFA500;
  }

  button.btn-primary {
    background-color: #FF8C00;
    border: none;
  }

  button.btn-primary:hover {
    background-color: #ffa500;
  }

  .alert-info {
    background-color: #2A2A2A;
    border-color: #FF8C00;
    color: #FFA500;
  }

  .alert-danger {
    background-color: #440000;
    border-color: #FF4500;
    color: #FF6347;
  }

  img.img-fluid {
    border: 2px solid #FFA500;
    border-radius: 6px;
  }

  /* Ссылки и прочий текст */
  a, a:hover {
    color: #FFB84D;
  }

</style>
</head>
<body>
<div class="container mt-4">
  <h2>Транзитивное замыкание (алгоритм Уоршелла)</h2>
  <form method="post" class="mb-3">
    <textarea name="matrix" class="form-control mb-3" rows="10"
      placeholder="Пример:&#10;0 1 0&#10;1 0 1&#10;0 1 0">{{ matrix or '' }}</textarea>
    <button type="submit" class="btn btn-primary">Вычислить</button>
  </form>

  {% if error %}
    <div class="alert alert-danger">{{ error }}</div>
  {% endif %}

  {% if result %}
    <div class="alert alert-info">
      <h5>Транзитивное замыкание:</h5>
      <pre class="bg-dark p-2 rounded border">{{ result }}</pre>
    </div>

    <h5>Граф достижимости:</h5>
    <img class="img-fluid border rounded" src="data:image/png;base64,{{ image }}">
  {% endif %}

  <div class="mt-4 small text-muted text-center">Created by Roman Stepanov. 2025.</div>
</div>
</body>
</html>

'''

@app.route('/', methods=['GET', 'POST'])
def index():
    matrix_str = ''
    result_str = ''
    img = None
    error_msg = None
    if request.method == 'POST':
        matrix_str = request.form['matrix']
        try:
            matrix = []
            for line in matrix_str.strip().split('\n'):
                row = [int(x) for x in line.strip().split()]
                matrix.append(row)
            n = len(matrix)
            if any(len(row) != n for row in matrix) or any(x not in (0,1) for row in matrix for x in row) or n == 0:
                error_msg = 'Ошибка: матрица должна быть квадратной и содержать только 0 и 1.'
            else:
                closure = warshall_reachability(matrix)
                result_str = '\n'.join(' '.join(str(x) for x in row) for row in closure)
                G = matrix_to_graph(closure)
                if G.number_of_edges() == 0:
                    img = None
                    error_msg = 'В графе после замыкания нет ни одного ребра для визуализации.'
                else:
                    img = plot_graph(G)
        except Exception as e:
            error_msg = f'Ошибка обработки данных: {e}'
    return render_template_string(html_template, matrix=matrix_str, result=result_str, image=img, error=error_msg)

if __name__ == '__main__':
    app.run(debug=True)
