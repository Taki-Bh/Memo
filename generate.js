const pptxgen = require('pptxgenjs');
let pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';

let slide = pres.addSlide();
slide.background = { color: '1E2761' };

slide.addText('Presentation Title', {
  x: 1.0,
  y: 2.0,
  w: 11.3,
  h: 1.0,
  fontSize: 44,
  bold: true,
  color: 'FFFFFF',
  align: 'center'
});

slide.addText('Created with pptxgenjs', {
  x: 1.0,
  y: 3.2,
  w: 11.3,
  h: 0.5,
  fontSize: 18,
  color: 'CADCFC',
  align: 'center'
});

pres.writeFile({ fileName: 'output.pptx' }).then(() => {
  console.log('File created successfully.');
});
