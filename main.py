import streamlit as st
import streamlit.components.v1 as components
import json
from st_bridge import bridge

st.set_page_config(layout="wide")
st.title("FoliarScope")

# Session state for tracking previous crop
if 'prev_crop' not in st.session_state:
    st.session_state.prev_crop = None
    
# Session state for percentage
if 'leaf_pct' not in st.session_state:
    st.session_state.leaf_pct = 0.0
    
# Select crop
crop = st.selectbox(
    "Select a crop leaf shape:",
    ["wheat", "pea", "potato", "tomato", "barley"],
)

# Voronoi parameters density slider
density = st.slider(
    "Number of cells:",
    min_value=10,
    max_value=200,
    value=45,
    step=1
)

# Constants for Voronoi parameters
ITERATIONS = 20
THINNESS = 0.22

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
      <title>Centroidal Voronoi Tessellation</title>
      <script src="https://d3js.org/d3.v7.min.js"></script>
      <script src="https://unpkg.com/d3-delaunay@6.0.2/dist/d3-delaunay.min.js"></script>
      <style>
        body {{ margin: 0; font-family: Arial, sans-serif; }}
        .container {{ display: flex; flex-direction: column; align-items: center; padding: 10px; }}
        canvas {{ border: 1px solid #ddd; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .info {{ margin-top: 15px; color: #555; font-size: 14px; }}
      </style>
    </head>
    <body>
    <div class="container">
      <canvas id="leafCanvas" width="500" height="500"></canvas>
      <div class="info">Click on cells to select/deselect areas</div>
    </div>
    
    <script>
      // Parse boundary and parameters
      const boundary = {boundary_json};
      const density = {density};
      const iterations = {ITERATIONS};  // Constant value
      const thinness = {THINNESS};      // Constant value
      const canvas = document.getElementById('leafCanvas');
      const ctx = canvas.getContext('2d');
      const width = canvas.width, height = canvas.height;
      
      // Colors
      const leafColor = '#4CAF50';
      const selectedColor = '#FF5722';
      const borderColor = 'rgba(255, 255, 255, 0.8)';
      const boundaryColor = '#2E7D32';
      
      // Build leaf polygon path
      const scaledBoundary = boundary.map(p => [p[0]*width, p[1]*height]);
      function createLeafPath() {{
        const path = new Path2D();
        path.moveTo(...scaledBoundary[0]);
        scaledBoundary.slice(1).forEach(pt => path.lineTo(...pt));
        path.closePath();
        return path;
      }}
      const leafPath = createLeafPath();
      
      // Function to calculate polygon area (shoelace formula)
      function polygonArea(poly) {{
        let area = 0;
        for (let i=0, n=poly.length; i<n; i++) {{
          const [x1, y1] = poly[i];
          const [x2, y2] = poly[(i+1) % n];
          area += x1*y2 - x2*y1;
        }}
        return Math.abs(area)/2;
      }}
      
      // Function to calculate polygon centroid
      function polygonCentroid(poly) {{
        let cx = 0, cy = 0;
        const n = poly.length;
        const area = polygonArea(poly);
        if (area === 0) return [0,0];
        
        for (let i=0; i<n; i++) {{
          const [x1, y1] = poly[i];
          const [x2, y2] = poly[(i+1) % n];
          const factor = (x1*y2 - x2*y1);
          cx += (x1 + x2) * factor;
          cy += (y1 + y2) * factor;
        }}
        return [cx/(6*area), cy/(6*area)];
      }}
      
      // Generate initial random points inside the leaf
      let points = [];
      while (points.length < density) {{
        const x = Math.random()*width;
        const y = Math.random()*height;
        if (ctx.isPointInPath(leafPath, x, y)) points.push([x, y]);
      }}
      
      // Relax points to create Centroidal Voronoi Tessellation
      function relaxPoints() {{
        // Create Delaunay triangulation
        const delaunay = d3.Delaunay.from(points);
        const voronoi = delaunay.voronoi([0, 0, width, height]);
        
        // Create new points by moving to centroids
        const newPoints = [];
        for (let i = 0; i < points.length; i++) {{
          const polygon = voronoi.cellPolygon(i);
          if (!polygon) {{
            newPoints.push(points[i]);
            continue;
          }}
          
          // Calculate centroid
          const [cx, cy] = polygonCentroid(polygon);
          
          // Apply thinness control - interpolate between current position and centroid
          const [px, py] = points[i];
          const nx = px * thinness + cx * (1 - thinness);
          const ny = py * thinness + cy * (1 - thinness);
          
          // Ensure new point is inside leaf
          if (ctx.isPointInPath(leafPath, nx, ny)) {{
            newPoints.push([nx, ny]);
          }} else {{
            newPoints.push(points[i]);
          }}
        }}
        return newPoints;
      }}
      
      // Perform relaxation iterations
      for (let i = 0; i < iterations; i++) {{
        points = relaxPoints();
      }}
      
      // Final Voronoi diagram
      const delaunay = d3.Delaunay.from(points);
      const voronoi = delaunay.voronoi([0, 0, width, height]);
      const cells = [];
      for (let i = 0; i < points.length; i++) {{
        const cell = voronoi.cellPolygon(i);
        if (cell) cells.push(cell);
      }}
      
      // Clicked cells
      const clicked = new Set();
      
      // Precompute the area of the entire leaf
      const totalLeafArea = polygonArea(scaledBoundary);
      
      // Render function
      function render() {{
        ctx.clearRect(0, 0, width, height);
        
        // Draw leaf boundary
        ctx.strokeStyle = boundaryColor;
        ctx.lineWidth = 2;
        ctx.stroke(leafPath);
        
        // Draw Voronoi cells
        ctx.save();
        ctx.clip(leafPath);
        cells.forEach((cell, idx) => {{
          const path = new Path2D();
          path.moveTo(...cell[0]);
          for (let i = 1; i < cell.length; i++) {{
            path.lineTo(...cell[i]);
          }}
          path.closePath();
          
          ctx.fillStyle = clicked.has(idx) ? selectedColor : leafColor;
          ctx.fill(path);
          ctx.strokeStyle = borderColor;
          ctx.lineWidth = 1;
          ctx.stroke(path);
        }});
        ctx.restore();
      }}
      
      // Find which cell contains a point
      function findCellIndex(x, y) {{
        for (let i = 0; i < cells.length; i++) {{
          const path = new Path2D();
          path.moveTo(...cells[i][0]);
          for (let j = 1; j < cells[i].length; j++) {{
            path.lineTo(...cells[i][j]);
          }}
          path.closePath();
          
          if (ctx.isPointInPath(path, x, y)) {{
            return i;
          }}
        }}
        return -1;
      }}
      
      // Calculate selected area percentage with single-pass pixel counting
      function calculateSelectedArea() {{
        if (cells.length === 0) return 0;
        
        // Create a temporary canvas
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = width;
        tempCanvas.height = height;
        const tempCtx = tempCanvas.getContext('2d');
        
        // Draw the entire leaf with background color
        const leafPathTemp = new Path2D();
        leafPathTemp.moveTo(...scaledBoundary[0]);
        scaledBoundary.slice(1).forEach(pt => leafPathTemp.lineTo(...pt));
        leafPathTemp.closePath();
        
        // Fill leaf with background color (light green)
        tempCtx.fillStyle = leafColor;
        tempCtx.fill(leafPathTemp);
        
        // Fill selected cells with selected color
        tempCtx.fillStyle = selectedColor;
        clicked.forEach(idx => {{
          const cell = cells[idx];
          const path = new Path2D();
          path.moveTo(...cell[0]);
          for (let i = 1; i < cell.length; i++) {{
            path.lineTo(...cell[i]);
          }}
          path.closePath();
          tempCtx.fill(path);
        }});
        
        // Count selected pixels (red channel > 200)
        const imageData = tempCtx.getImageData(0, 0, width, height);
        const data = imageData.data;
        let selectedPixels = 0;
        let leafPixels = 0;
        
        for (let i = 0; i < data.length; i += 4) {{
          // Count leaf pixels (anything not background)
          if (data[i] > 0 || data[i+1] > 0 || data[i+2] > 0) {{
            leafPixels++;
          }}
          
          // Count selected pixels (red channel dominates)
          if (data[i] > 200 && data[i+1] < 100 && data[i+2] < 100) {{
            selectedPixels++;
          }}
        }}
        
        // Calculate percentage
        return (selectedPixels / leafPixels) * 100;
      }}
      
      // Click handler
      canvas.addEventListener('click', e => {{
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Only process if inside leaf
        if (ctx.isPointInPath(leafPath, x, y)) {{
          const idx = findCellIndex(x, y);
          if (idx !== -1) {{
            clicked.has(idx) ? clicked.delete(idx) : clicked.add(idx);
            render();
            
            // Calculate and send percentage
            const pct = calculateSelectedArea().toFixed(2);
            if (window.top.stBridges) {{
              window.top.stBridges.send('leaf-bridge', pct);
            }}
          }}
        }}
      }});
      
      // Initial render
      render();
    </script>
    </body>
    </html>
    """,
    height=600,
)

#Bridging JS to Python-Streamlit
# Listen for bridge updates
leaf_data = bridge("leaf-bridge", default=None)
if leaf_data is not None:
    try:
        st.session_state.leaf_pct = float(leaf_data)
    except Exception:
        pass
# Reset percentage if crop changed
if st.session_state.prev_crop != crop:
    st.session_state.leaf_pct = 0.0
    st.session_state.prev_crop = crop

# Display information
st.markdown(f"**Selected area:** `{st.session_state.leaf_pct}%` of leaf")
st.markdown("[Note: Centroidal Voronoi Tessellation, not Delaunay Triangulation]")
