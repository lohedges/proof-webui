// Variables for referencing the background, foreground, canvas, and 2dcanvas context.
var background, foreground, canvas, ctx;

// Variable for the background micrograph image.
var micrograph = new Image();

// Variable for the foreground micrograph labels.
var average = new Image();
average.isActive = false;

// Variables to keep track of the mouse position and status.
var mouseX, mouseY, mouseDown = false, middleButton = false;

// Variables to keep track of the touch position.
var touchX, touchY;

// Keep track of the old/last position when drawing a line.
// Initialise to -1 as "undefined".
var lastX, lastY=-1;

// Arrays to store the current filament path and the set of paths.
var path = [], paths = [];

// Initalise a slider to allow the user to adjust the line width.
var slider = document.getElementById("lineWidthSlider");
var sliderVal = document.getElementById("sliderLineWidth");
sliderVal.innerHTML = slider.value;
var lineWidth = slider.value;

// Initalise the drawing mode label.
var drawingMode = document.getElementById("drawingMode");
drawingMode.innerHTML = "Freehand";

// Function to dynamically update the line width.
slider.oninput = function()
{
    sliderVal.innerHTML = this.value;
    lineWidth = sliderVal.innerHTML;
    redraw(canvas, ctx);
}

// Draws a line between the specified position on the supplied canvas name
// Parameters are:
//     ctx       A canvas context,
//	   x         The x position.
//	   y         The y position.
//     savePath  Whether to save the current path.
function drawLine(ctx, x, y, savePath)
{
    // If lastX is not set, set lastX and lastY to the current position.
    if (lastX == -1)
    {
        lastX = x;
        lastY = y;
    }

    // Red, full opacity.
    r=255; g=0; b=0; a=255;

    // Select a fill style
    ctx.strokeStyle = "rgba("+r+","+g+","+b+","+(a/255)+")";

    // Set the line "cap" style to round, so lines at different angles can
    // join into each other.
    ctx.lineCap = "round";

    // Draw a filled line.
    ctx.beginPath();

    // First, move to the old (previous) position.
    ctx.moveTo(lastX, lastY);

    // Now draw a line to the current touch/pointer position.
    ctx.lineTo(x, y);

    // Set the line thickness and draw the line.
    ctx.lineWidth = lineWidth;
    ctx.stroke();

    ctx.closePath();

    // Update the last position to reference the current position.
    lastX = x;
    lastY = y;

    // Store the coordinates in the current path.
    if (savePath) {
        path.push([x, y]);
    }
}

// Clear the canvas context using the canvas width and height.
function clearAll(canvas, ctx, clearPaths)
{
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Clear the array of paths.
    if (clearPaths)
    {
        paths = [];
    }

    // Update the drawing mode.
    drawingMode.innerHTML = "Freehand";
}

// Return a new micrograph image.
function newMicrograph(canvas, ctx)
{
    clearAll(canvas, ctx, true);
    randomMicrograph();
}

// Upload the labelled image to the webserver.
function upload(canvas, ctx)
{
    var dataUrl = canvas.toDataURL('image/png');

    $.get('/label/upload',
          {index: micrograph.index, dataUrl: dataUrl},
          function(response)
          {
          }
    );

    clearAll(canvas, ctx, true);
    randomMicrograph();
}

// Load a random micrograph.
function randomMicrograph()
{
	$.get('/label/micrograph',
          function(response)
          {
              // Change the background canvas, ensuring that the micrograph has loaded.
              micrograph.onload = function()
              {
                  // Get the specific background and canvas elements from the HTML document.
                  background = document.getElementById('background');

                  // Draw the micrograph on the background layer.
                  if (background.getContext)
                  {
                      background.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
                      background.getContext('2d').drawImage(micrograph, 0, 0);
                  }
              }
              micrograph.src = "../" + response.micrograph;
              micrograph.index = response.index;
          }
    );
}

// Toggle displaying the average micrograph labels.
function toggleAverage()
{
    if (!average.isActive)
    {
        $.get('/label/average',
            {index: micrograph.index, average: average.src},
            function(response)
            {
                // Change the foreground canvas, ensuring that the image has loaded.
                average.onload = function()
                {
                    // Get the specific foreground element from the HTML document.
                    foreground = document.getElementById('foreground');

                    // Draw the average on the foreground layer.
                    if (foreground.getContext)
                    {
                        foreground.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
                        foreground.getContext('2d').drawImage(average, 0, 0);
                    }
                }
                if (response.average != "NULL")
                {
                    average.src = "../" + response.average;
                    average.isActive = true;
                }
            }
        );
    }
    else
    {
        // Get the specific foreground element from the HTML document.
        foreground = document.getElementById('foreground');

        // Draw the average on the foreground layer.
        if (foreground.getContext)
        {
            foreground.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
        }

        average.isActive = false;
    }
}

// Clear the last filament path.
function clearLast(canvas, ctx)
{
    // First, clear the canvas.
    clearAll(canvas, ctx, false);

    // Draw all paths apart from most recent path.
    for (var i = 0; i<paths.length-1; i++)
    {
        for (var j=0; j<paths[i].length; j++)
        {
            drawLine(ctx, paths[i][j][0], paths[i][j][1], false);
        }

        lastX = -1;
        lastY = -1;
    }

    // Remove the last path.
    paths.pop();
}

// Redraw all paths, e.g. after a change in line width.
function redraw(canvas, ctx)
{
    // First, clear the canvas.
    clearAll(canvas, ctx, false);

    // Draw all paths.
    for (var i = 0; i<paths.length; i++)
    {
        for (var j=0; j<paths[i].length; j++)
        {
            drawLine(ctx, paths[i][j][0], paths[i][j][1], false);
        }

        lastX = -1;
        lastY = -1;
    }
}

// Keep track of the mouse button being pressed and draw a dot at current location
function labeller_mouseDown(e)
{
   // Handle different event models
    var event = e || window.event;
    var btnCode;

	if ('object' === typeof event)
    {
        btnCode = event.button;

        // Left-click.
        if (btnCode == 0)
        {
            // Disable middle-click mode.
            if (middleButton)
            {
                labeller_mouseUp;
                middleButton = false;
            }

            // Update the drawing mode.
            drawingMode.innerHTML = "Freehand";

            mouseDown = true;
            drawLine(ctx, mouseX, mouseY, true);
        }
		// Middle-click.
        else if (btnCode == 1)
        {
            // Update the drawing mode.
            drawingMode.innerHTML = "Line";

            middleButton = true;
            // Make sure we draw a dot for start point.
            drawLine(ctx, mouseX, mouseY, true);
            // Flag that mouse is no-longer down.
            mouseDown = false;
            drawLine(ctx, mouseX, mouseY, true);
        }
        // Right-click.
        else if (btnCode == 2)
        {
            middleButton = false;
            labeller_mouseUp();
        }
    }
}

// Keep track of the mouse button being released
function labeller_mouseUp()
{
    if (!middleButton)
    {
        mouseDown = false;

        // Reset lastX and lastY to -1 to indicate that they are now invalid,
        // since we have lifted the "pen".
        lastX = -1;
        lastY = -1;

        // Store the path.
        if (path.length > 0)
        {
            paths.push(path);
            path = [];
        }
    }
}

// Keep track of the mouse position and draw a dot if mouse button is currently pressed.
function labeller_mouseMove(e)
{
    // Update the mouse coordinates when moved.
    getMousePos(e);

    // Draw a dot if the mouse button is currently being pressed.
    if (mouseDown)
    {
        drawLine(ctx, mouseX, mouseY, true);
    }
}

// Get the current mouse position relative to the top-left of the canvas.
function getMousePos(e)
{
    if (!e)
        var e = event;

    if (e.offsetX)
    {
        mouseX = e.offsetX;
        mouseY = e.offsetY;
    }
    else if (e.layerX)
    {
        mouseX = e.layerX;
        mouseY = e.layerY;
    }
}

// Draw something when a touch start is detected.
function labeller_touchStart()
{
    // Update the touch coordinates
    getTouchPos();

    drawLine(ctx, touchX, touchY, true);

    // Prevents an additional mousedown event being triggered.
    event.preventDefault();
}

function labeller_touchEnd()
{
    // Reset lastX and lastY to -1 to indicate that they are now invalid,
    // since we have lifted the "pen"
    lastX = -1;
    lastY = -1;

    // Store the path
    paths.push(path);
    path = [];
}

// Draw something and prevent the default scrolling when touch movement is detected.
function labeller_touchMove(e)
{
    // Update the touch coordinates.
    getTouchPos(e);

    // During a touchmove event, unlike a mousemove event, we don't need to
    // check if the touch is engaged, since there will always be contact with
    // the screen by definition.
    drawLine(ctx, touchX, touchY, true);

    // Prevent a scrolling action as a result of this touchmove triggering.
    event.preventDefault();
}

// Get the touch position relative to the top-left of the canvas.
// When we get the raw values of pageX and pageY below, they take into
// account the scrolling on the page but not the position relative to our
// target div. We'll adjust them using "target.offsetLeft" and
// "target.offsetTop" to get the correct values in relation to the top
// left of the canvas.
function getTouchPos(e)
{
    if (!e)
        var e = event;

    if (e.touches)
    {
        // Only deal with one finger.
        if (e.touches.length == 1)
        {
            // Get the information for finger #1
            var touch = e.touches[0];
            touchX = touch.pageX-touch.target.offsetLeft;
            touchY = touch.pageY-touch.target.offsetTop;
        }
    }
}

// Set-up the canvas and add our event handlers after the page has loaded.
function init()
{
    // Get the specific background and canvas elements from the HTML document.
    background = document.getElementById('background');
    canvas = document.getElementById('labeller');

    // Load a random micrograph.
    randomMicrograph();

    // Draw the micrograph on the background layer.
    if (background.getContext)
    {
        background.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
        background.getContext('2d').drawImage(micrograph, 0, 0);
    }

    // If the browser supports the canvas tag, get the 2d drawing context
    // for this canvas.
    if (canvas.getContext)
        ctx = canvas.getContext('2d');

    // Check that we have a valid context to draw on/with before adding
    // event handlers.
    if (ctx)
    {
        // React to mouse events on the canvas, and mouseup on the entire
        // document.
        canvas.addEventListener('mousedown', labeller_mouseDown, false);
        canvas.addEventListener('mousemove', labeller_mouseMove, false);
        window.addEventListener('mouseup', labeller_mouseUp, false);

        // React to touch events on the canvas.
        canvas.addEventListener('touchstart', labeller_touchStart, false);
        canvas.addEventListener('touchend', labeller_touchEnd, false);
        canvas.addEventListener('touchmove', labeller_touchMove, false);

		// Disable context menu on right-click.
        canvas.oncontextmenu = function (event)
		{
			event.preventDefault();
		}
    }
}
