import streamlit as st
import streamlit.components.v1 as components
import json
from st_bridge import bridge  # Import bridge for communication

st.set_page_config(layout="wide")
st.title("FoliarScope")

# Session state for percentage
if 'leaf_pct' not in st.session_state:
    st.session_state.leaf_pct = 0.0

# Select crop
crop = st.selectbox(
    "Select a crop leaf shape:",
    ["wheat", "pea", "potato", "tomato", "barley"],
)

# Adjust slider min for potato
if crop == 'potato':
    min_res = 0.09
else:
    min_res = 0.03

# Grid resolution slider
grid_resolution = st.slider(
    "Grid resolution (square size fraction of canvas):",
    min_value=min_res,
    max_value=0.3,
    value=min_res,
    step=0.03,
)

# Predefined leaf shapes
LEAF_SHAPES = {
    "wheat": [[0.1,0.9],[0.2,0.7],[0.4,0.4],[0.6,0.2],[0.8,0.1],[0.9,0.2],[0.6,0.5],[0.4,0.8],[0.2,0.95]],
    "pea":   [[0.5,0.9],[0.65,0.7],[0.75,0.5],[0.8,0.3],[0.5,0.1],[0.2,0.3],[0.25,0.5],[0.35,0.7]],
    "potato":[[0.2,0.2],[0.3,0.15],[0.5,0.1],[0.7,0.15],[0.8,0.3],[0.85,0.5],[0.8,0.7],[0.65,0.85],[0.4,0.9],[0.2,0.8],[0.15,0.5]],
    "tomato":[[0.5,0.95],[0.7,0.8],[0.85,0.6],[0.9,0.4],[0.85,0.2],[0.6,0.05],[0.4,0.05],[0.15,0.2],[0.1,0.4],[0.15,0.6],[0.3,0.8]],
    "barley":[[0.5,0.1],[0.52,0.3],[0.54,0.5],[0.56,0.7],[0.5,0.9],[0.48,0.7],[0.46,0.5],[0.44,0.3]]
}

boundary_json = json.dumps(LEAF_SHAPES[crop])
res = grid_resolution  # shorter alias for formatting

components.html(f"""
<!DOCTYPE html>
<html>
<head>
  <script src="https://unpkg.com/martinez-polygon-clipping@0.7.0/dist/martinez.umd.js"></script>
</head>
<body>
<canvas id="leafCanvas" width="500" height="500" style="border:1px solid #ccc"></canvas>
<script>
  // inputs from Python
  const boundary = {boundary_json};
  const W = 500, H = 500;
  const gridSize = {res} * W;

  // helper: shoelace formula
  function shoelace(ring) {{
    let A = 0, n = ring.length;
    for (let i = 0; i < n; i++) {{
      const j = (i + 1) % n;
      A += ring[i][0] * ring[j][1] - ring[j][0] * ring[i][1];
    }}
    return Math.abs(A) / 2;
  }}

  // scale boundary
  const scaled = boundary.map(p => [p[0] * W, p[1] * H]);
  const closed = [...scaled, scaled[0]];

  // compute total leaf area
  const totalLeafArea = shoelace(closed);

  // build leaf outline path
  const leafPath = new Path2D();
  leafPath.moveTo(...scaled[0]);
  scaled.slice(1).forEach(pt => leafPath.lineTo(...pt));
  leafPath.closePath();

  // generate and clip grid cells
  const cells = [];
  const minX = Math.min(...scaled.map(p => p[0])), maxX = Math.max(...scaled.map(p => p[0]));
  const minY = Math.min(...scaled.map(p => p[1])), maxY = Math.max(...scaled.map(p => p[1]));
  const iMin = Math.floor(minX / gridSize), iMax = Math.ceil(maxX / gridSize);
  const jMin = Math.floor(minY / gridSize), jMax = Math.ceil(maxY / gridSize);

  for (let i = iMin; i < iMax; i++) {{
    for (let j = jMin; j < jMax; j++) {{
      const x = i * gridSize, y = j * gridSize;
      const square = [[x,y],[x+gridSize,y],[x+gridSize,y+gridSize],[x,y+gridSize],[x,y]];
      const clipped = martinez.intersection([square], [closed]);
      if (!clipped || clipped.length === 0) continue;
      const path = new Path2D();
      let area = 0;
      for (const poly of clipped) {{
        for (const ring of poly) {{
          const a = shoelace(ring);
          area += a;
          if (a < 1) continue;
          path.moveTo(...ring[0]);
          for (let k = 1; k < ring.length; k++) path.lineTo(...ring[k]);
          path.closePath();
        }}
      }}
      if (area < 1) continue;
      cells.push({{ id: `${{i}}_${{j}}`, path, area }});
    }}
  }}

  // setup canvas
  const canvas = document.getElementById('leafCanvas');
  const ctx = canvas.getContext('2d');
  const clicked = new Set();

  function render() {{
    ctx.clearRect(0,0,W,H);
    ctx.save(); ctx.clip(leafPath);
    for (const c of cells) {{
      ctx.fillStyle = clicked.has(c.id) ? 'rgba(255,0,0,0.7)' : 'rgba(144,238,144,0.5)';
      ctx.fill(c.path);
      ctx.stroke(c.path);
    }}
    ctx.restore();
    ctx.strokeStyle='black'; ctx.lineWidth=2; ctx.stroke(leafPath);
  }}

  canvas.addEventListener('click', e => {{
    const r = canvas.getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    if (!ctx.isPointInPath(leafPath,x,y)) return;
    for (const c of cells) if (ctx.isPointInPath(c.path,x,y)) {{
      clicked.has(c.id)? clicked.delete(c.id): clicked.add(c.id);
      break;
    }}
    render();
    let sel = 0;
    clicked.forEach(id => {{ const c = cells.find(u=>u.id===id); if(c) sel += c.area; }});
    const pct = (sel/totalLeafArea*100).toFixed(2);
    window.top.stBridges?.send('leaf-bridge', pct);
  }});

  render();
</script>
</body>
</html>
""", height=620)

# Listen for bridge updates
leaf_data = bridge('leaf-bridge', default=None)
if leaf_data is not None:
    try:
        st.session_state.leaf_pct = float(leaf_data)
    except:
        pass

st.markdown(f"**Selected area:** {st.session_state.leaf_pct}% of leaf")
