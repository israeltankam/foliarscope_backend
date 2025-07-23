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

# Grid resolution slider
grid_resolution = st.slider(
    "Grid resolution (square size):", 0.03, 0.3, 0.06, 0.03
)

# Predefined leaf shapes
LEAF_SHAPES = {
    "wheat": [[0.1,0.9],[0.2,0.7],[0.4,0.4],[0.6,0.2],[0.8,0.1],[0.9,0.2],[0.6,0.5],[0.4,0.8],[0.2,0.95]],
    "pea": [[0.5,0.9],[0.65,0.7],[0.75,0.5],[0.8,0.3],[0.5,0.1],[0.2,0.3],[0.25,0.5],[0.35,0.7]],
    "potato": [[0.2,0.2],[0.3,0.15],[0.5,0.1],[0.7,0.15],[0.8,0.3],[0.85,0.5],[0.8,0.7],[0.65,0.85],[0.4,0.9],[0.2,0.8],[0.15,0.5]],
    "tomato": [[0.5,0.95],[0.7,0.8],[0.85,0.6],[0.9,0.4],[0.85,0.2],[0.6,0.05],[0.4,0.05],[0.15,0.2],[0.1,0.4],[0.15,0.6],[0.3,0.8]],
    "barley": [[0.5,0.1],[0.52,0.3],[0.54,0.5],[0.56,0.7],[0.5,0.9],[0.48,0.7],[0.46,0.5],[0.44,0.3]]
}

# Prepare JSON-encoded boundary
boundary_json = json.dumps(LEAF_SHAPES[crop])

# Create the interactive component
components.html(
    f"""
    <!DOCTYPE html>
    <html>
    <head>
      <script src="https://unpkg.com/martinez-polygon-clipping@0.7.0/dist/martinez.umd.js"></script>
    </head>
    <body>
    <canvas id="leafCanvas" width="500" height="500" style="border:1px solid #ccc"></canvas>
    <script>
      // Parse boundary and grid resolution
      const boundary = {boundary_json};
      const gridResolution = {grid_resolution};
      const canvas = document.getElementById('leafCanvas');
      const ctx = canvas.getContext('2d');
      const width = canvas.width, height = canvas.height;

      // Build leaf polygon path
      const scaledBoundary = boundary.map(p => [p[0]*width, p[1]*height]);
      const leafPolygonClosed = [...scaledBoundary, scaledBoundary[0]];
      
      function createLeafPath() {{
        const path = new Path2D();
        path.moveTo(...scaledBoundary[0]);
        scaledBoundary.slice(1).forEach(pt => path.lineTo(...pt));
        path.closePath();
        return path;
      }}
      const leafPath = createLeafPath();

      // Shoelace formula for polygon area
      function polygonArea(ring) {{
        let area = 0;
        const n = ring.length;
        for (let i=0; i<n; i++) {{
          const j = (i+1) % n;
          area += ring[i][0]*ring[j][1] - ring[j][0]*ring[i][1];
        }}
        return Math.abs(area) / 2;
      }}

      // Compute leaf area
      const totalLeafArea = polygonArea(leafPolygonClosed);

      // Generate grid
      const gridSize = gridResolution * width;
      const minX = Math.min(...scaledBoundary.map(p => p[0]));
      const maxX = Math.max(...scaledBoundary.map(p => p[0]));
      const minY = Math.min(...scaledBoundary.map(p => p[1]));
      const maxY = Math.max(...scaledBoundary.map(p => p[1]));
      
      const iMin = Math.floor(minX / gridSize);
      const iMax = Math.ceil(maxX / gridSize);
      const jMin = Math.floor(minY / gridSize);
      const jMax = Math.ceil(maxY / gridSize);
      
      const gridCells = [];
      const gridCellsById = {{}};
      
      // Generate grid cells and clip to leaf
      for (let i = iMin; i < iMax; i++) {{
        for (let j = jMin; j < jMax; j++) {{
          const x = i * gridSize;
          const y = j * gridSize;
          
          // Create square cell
          const cellPolygon = [
            [x, y],
            [x+gridSize, y],
            [x+gridSize, y+gridSize],
            [x, y+gridSize],
            [x, y]  // Close polygon
          ];
          
          // Clip cell to leaf
          const result = martinez.intersection([cellPolygon], [leafPolygonClosed]);
          
          if (result.length > 0) {{
            // Calculate area of clipped polygon
            let cellArea = 0;
            for (let poly of result) {{
              for (let ring of poly) {{
                cellArea += polygonArea(ring);
              }}
            }}
            
            const id = `${{i}}_${{j}}`;
            const cell = {{ id, polygon: result, area: cellArea }};
            gridCells.push(cell);
            gridCellsById[id] = cell;
          }}
        }}
      }}

      // Create grid lines path
      function createGridLinesPath() {{
        const path = new Path2D();
        // Vertical lines
        for (let i = iMin; i <= iMax; i++) {{
          const x = i * gridSize;
          path.moveTo(x, minY);
          path.lineTo(x, maxY);
        }}
        // Horizontal lines
        for (let j = jMin; j <= jMax; j++) {{
          const y = j * gridSize;
          path.moveTo(minX, y);
          path.lineTo(maxX, y);
        }}
        return path;
      }}
      const gridLinesPath = createGridLinesPath();

      // Clickable rendering
      const clicked = new Set();
      function render() {{
        ctx.clearRect(0, 0, width, height);
        ctx.save(); 
        ctx.clip(leafPath);
        
        // Render grid cells
        gridCells.forEach(cell => {{
          const path = new Path2D();
          for (let poly of cell.polygon) {{
            for (let ring of poly) {{
              path.moveTo(...ring[0]);
              for (let k=1; k<ring.length; k++) {{
                path.lineTo(...ring[k]);
              }}
              path.closePath();
            }}
          }}
          
          ctx.fillStyle = clicked.has(cell.id) ? 'rgba(255, 0, 0, 0.7)' : 'rgba(144, 238, 144, 0.5)';
          ctx.fill(path);
        }});
        
        // Draw grid lines on top
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 0.7;
        ctx.stroke(gridLinesPath);
        
        ctx.restore();
        
        // Draw leaf outline
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 2;
        ctx.stroke(leafPath);
      }}

      canvas.addEventListener('click', e => {{
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Only process if inside leaf
        if (ctx.isPointInPath(leafPath, x, y)) {{
          const i = Math.floor(x / gridSize);
          const j = Math.floor(y / gridSize);
          const id = `${{i}}_${{j}}`;
          
          if (gridCellsById[id]) {{
            clicked.has(id) ? clicked.delete(id) : clicked.add(id);
            render();
            
            // Compute selected area
            let selectedArea = 0;
            clicked.forEach(id => {{
              selectedArea += gridCellsById[id].area;
            }});
            
            const pct = (selectedArea / totalLeafArea * 100).toFixed(2);
            
            // Send to Streamlit via bridge
            if (window.top.stBridges) {{
              window.top.stBridges.send('leaf-bridge', pct);
            }}
          }}
        }}
      }});

      // Initial draw
      render();
    </script>
    </body>
    </html>
    """,
    height=600,
)

# Listen for bridge updates
leaf_data = bridge("leaf-bridge", default=None)
if leaf_data is not None:
    try:
        st.session_state.leaf_pct = float(leaf_data)
    except Exception:
        pass

st.markdown(f"**Selected area:** {st.session_state.leaf_pct}% of leaf")