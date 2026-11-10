'use strict';
(() => {
  const node = document.getElementById('chart-data');
  if (!node || !window.echarts) return;
  const data = JSON.parse(node.dataset.charts);
  const colors = ['#284e68','#a33a43','#738d9f','#b28b55','#5d827c','#8e7491','#a1ad89','#c19196'];
  const charts = [];
  const label = {color:'#6b8092',fontSize:11};
  function draw(id, option, rows) {
    const el = document.getElementById(id);
    if (!el) return;
    const chart = echarts.init(el);
    chart.setOption({color:colors,animation:!window.matchMedia('(prefers-reduced-motion: reduce)').matches,textStyle:{fontFamily:'PingFang SC, Microsoft YaHei, sans-serif'},...option,
      ...(rows.length ? {} : {title:{text:'暂无符合条件的销售数据',left:'center',top:'center',textStyle:{fontSize:14,fontWeight:'normal',color:'#8792a5'}}})});
    charts.push(chart);
  }
  draw('monthly-chart',{
    tooltip:{trigger:'axis',valueFormatter:v=>Number(v).toLocaleString(undefined,{maximumFractionDigits:2})},
    grid:{left:62,right:28,top:30,bottom:40},
    xAxis:{type:'category',data:data.months.map(x=>x.month),axisLine:{lineStyle:{color:'#e9edf4'}},axisTick:{show:false},axisLabel:label,boundaryGap:false},
    yAxis:{type:'value',splitLine:{lineStyle:{color:'#eef1f6',type:'dashed'}},axisLabel:{...label,formatter:v=>v>=1000?`${Math.round(v/1000)}k`:v}},
    series:[{name:'销售额',data:data.months.map(x=>Number(x.amount)),type:'line',smooth:0.18,symbol:'circle',symbolSize:4,lineStyle:{width:2.5},itemStyle:{color:colors[0]},areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(40,78,104,.12)'},{offset:1,color:'rgba(40,78,104,.005)'}])}}]
  },data.months);
  draw('category-chart',{
    tooltip:{trigger:'item',valueFormatter:v=>Number(v).toLocaleString(undefined,{maximumFractionDigits:2})},
    legend:{bottom:7,left:'center',type:'scroll',icon:'circle',itemWidth:8,itemHeight:8,textStyle:{...label,fontSize:11}},
    series:[{type:'pie',radius:['45%','69%'],center:['50%','43%'],avoidLabelOverlap:true,itemStyle:{borderColor:'#fff',borderWidth:4,borderRadius:3},label:{show:false},emphasis:{label:{show:true,fontSize:14,fontWeight:'bold'}},data:data.categories.map(x=>({name:x.CategoryName,value:Number(x.amount)}))}]
  },data.categories);
  function bars(id, rows, metric, name) {
    const list=[...rows].reverse();
    draw(id,{tooltip:{trigger:'axis',axisPointer:{type:'shadow'},valueFormatter:v=>Number(v).toLocaleString(undefined,{maximumFractionDigits:2})},
      grid:{left:170,right:35,top:20,bottom:30},xAxis:{type:'value',axisLabel:label,splitLine:{lineStyle:{color:'#eef1f6'}}},
      yAxis:{type:'category',data:list.map(x=>x.ProductName),axisLabel:{...label,width:150,overflow:'truncate'},axisLine:{show:false},axisTick:{show:false}},
      series:[{name,type:'bar',data:list.map(x=>Number(x[metric])),barMaxWidth:16,itemStyle:{borderRadius:[0,4,4,0],color:id==='volume-chart'?colors[1]:colors[0]}}]},rows);
  }
  bars('product-chart',data.top_products,'amount','销售额');
  bars('volume-chart',data.volume,'quantity','销量');
  const resize = () => charts.forEach(chart => chart.resize());
  window.addEventListener('resize',resize);
  if (window.ResizeObserver) {
    const observer = new ResizeObserver(resize);
    document.querySelectorAll('.chart').forEach(el => observer.observe(el));
  }
})();
