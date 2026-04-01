import { useEffect, useRef, useState } from "react";
import { Calendar, ChevronDown, Download, Truck, Activity, AlertOctagon, Gauge } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, PieChart, Pie } from 'recharts';

const trendData = [
  { day: 'Mon', critical: 2, moderate: 5, advisory: 12 },
  { day: 'Tue', critical: 1, moderate: 4, advisory: 10 },
  { day: 'Wed', critical: 4, moderate: 6, advisory: 15 },
  { day: 'Thu', critical: 0, moderate: 3, advisory: 8 },
  { day: 'Fri', critical: 3, moderate: 7, advisory: 14 },
  { day: 'Sat', critical: 1, moderate: 2, advisory: 5 },
  { day: 'Sun', critical: 0, moderate: 1, advisory: 4 },
];

const riskData = [
  { name: 'Speeding', value: 45, color: '#0A2559' },
  { name: 'Distraction', value: 30, color: '#ba1a1a' },
  { name: 'Tailgating', value: 15, color: '#515f74' },
  { name: 'Other', value: 10, color: '#c5c6d1' },
];

interface DashboardProps {
  onNavigate: (view: "dashboard" | "incident" | "alerts") => void;
}

function useElementSize<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const element = ref.current;
    if (!element) {
      return;
    }

    const updateSize = () => {
      const nextWidth = Math.max(0, element.clientWidth);
      const nextHeight = Math.max(0, element.clientHeight);
      setSize({ width: nextWidth, height: nextHeight });
    };

    updateSize();

    const resizeObserver = new ResizeObserver(() => {
      updateSize();
    });
    resizeObserver.observe(element);

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  return { ref, width: size.width, height: size.height };
}

export function Dashboard({ onNavigate }: DashboardProps) {
  const trendsChart = useElementSize<HTMLDivElement>();
  const riskChart = useElementSize<HTMLDivElement>();

  return (
    <div className="p-10 flex flex-col gap-8 max-w-[1600px]">
      {/* Metrics Grid Header */}
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-primary">Fleet Intelligence Overview</h2>
          <p className="text-secondary font-medium text-sm mt-1">Real-time analytical dossier for global fleet operations.</p>
        </div>
        <div className="flex gap-3">
          <div className="relative">
            <button className="flex items-center gap-2 bg-surface-container-lowest ring-1 ring-outline-variant/15 shadow-sm px-4 py-2.5 rounded-lg font-bold text-xs hover:bg-surface-container-low transition-colors text-on-surface-variant">
              <Calendar className="w-4 h-4" />
              <span>Oct 1, 2023 - Oct 31, 2023</span>
              <ChevronDown className="w-4 h-4 text-outline" />
            </button>
          </div>
          <button className="flex items-center gap-2 bg-primary text-on-primary px-4 py-2.5 rounded-lg font-bold text-xs hover:opacity-90 shadow-md transition-opacity">
            <Download className="w-4 h-4" />
            <span>Export Report</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm flex flex-col justify-between">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-primary-container/20 rounded-lg text-primary">
              <Truck className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md">+2.4%</span>
          </div>
          <div>
            <p className="text-xs font-bold text-secondary uppercase tracking-wider mb-1">Active Assets</p>
            <h3 className="text-3xl font-black text-primary tracking-tight">1,248</h3>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm flex flex-col justify-between">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-tertiary-container/20 rounded-lg text-tertiary">
              <Activity className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-bold text-error bg-error-container px-2 py-1 rounded-md">-1.2%</span>
          </div>
          <div>
            <p className="text-xs font-bold text-secondary uppercase tracking-wider mb-1">Avg Risk Score</p>
            <h3 className="text-3xl font-black text-primary tracking-tight">82.4<span className="text-sm text-outline font-medium">/100</span></h3>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm flex flex-col justify-between">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-error-container text-error rounded-lg">
              <AlertOctagon className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-bold text-error bg-error-container px-2 py-1 rounded-md">+5.1%</span>
          </div>
          <div>
            <p className="text-xs font-bold text-secondary uppercase tracking-wider mb-1">Critical Incidents</p>
            <h3 className="text-3xl font-black text-primary tracking-tight">14</h3>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm flex flex-col justify-between">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-secondary-container/50 text-secondary rounded-lg">
              <Gauge className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md">+0.8%</span>
          </div>
          <div>
            <p className="text-xs font-bold text-secondary uppercase tracking-wider mb-1">Fuel Efficiency</p>
            <h3 className="text-3xl font-black text-primary tracking-tight">6.8<span className="text-sm text-outline font-medium"> mpg</span></h3>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Violation Trends */}
        <div className="lg:col-span-8 min-w-0 bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm flex flex-col">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h3 className="text-lg font-bold text-primary">Violation Trends</h3>
              <p className="text-xs text-secondary">Daily incident frequency across the current month</p>
            </div>
            <div className="flex bg-surface-container-low p-1 rounded-lg ring-1 ring-outline-variant/15">
              <button className="px-3 py-1.5 text-[11px] font-bold bg-surface-container-lowest ring-1 ring-outline-variant/15 shadow-sm rounded-md text-primary">Daily</button>
              <button className="px-3 py-1.5 text-[11px] font-bold text-secondary hover:text-primary">Weekly</button>
            </div>
          </div>
          <div ref={trendsChart.ref} className="h-72 w-full min-w-0 flex flex-col pt-4">
            {trendsChart.width > 0 && trendsChart.height > 0 && (
              <BarChart width={trendsChart.width} height={trendsChart.height} data={trendData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e0e3e5" />
                <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#757780', fontWeight: 700 }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#757780', fontWeight: 700 }} />
                <Tooltip 
                  cursor={{ fill: '#f2f4f6' }}
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e0e3e5', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  labelStyle={{ fontWeight: 'bold', color: '#191c1e', marginBottom: '4px' }}
                />
                <Bar dataKey="advisory" stackId="a" fill="#515f74" radius={[0, 0, 4, 4]} />
                <Bar dataKey="moderate" stackId="a" fill="#0A2559" />
                <Bar dataKey="critical" stackId="a" fill="#ba1a1a" radius={[4, 4, 0, 0]} />
              </BarChart>
            )}
          </div>
          <div className="flex items-center gap-6 pt-4 border-t border-surface-container-high mt-4">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-error"></span>
              <span className="text-[10px] font-bold uppercase tracking-wide text-secondary">Critical</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-primary"></span>
              <span className="text-[10px] font-bold uppercase tracking-wide text-secondary">Moderate</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-secondary"></span>
              <span className="text-[10px] font-bold uppercase tracking-wide text-secondary">Advisory</span>
            </div>
            <div className="ml-auto text-[10px] text-outline italic font-medium">Updated: 2 mins ago</div>
          </div>
        </div>

        {/* Risk Composition */}
        <div className="lg:col-span-4 min-w-0 bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm flex flex-col">
          <div className="mb-6">
            <h3 className="text-lg font-bold text-primary">Risk Composition</h3>
            <p className="text-xs text-secondary">Breakdown of primary behavioral risks</p>
          </div>
          <div className="flex-1 flex flex-col justify-center">
            <div ref={riskChart.ref} className="relative w-full min-w-0 h-48 mb-4">
              {riskChart.width > 0 && riskChart.height > 0 && (
                <PieChart width={riskChart.width} height={riskChart.height}>
                  <Pie
                    data={riskData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                    stroke="none"
                  >
                    {riskData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: '1px solid #e0e3e5', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    itemStyle={{ fontWeight: 'bold', color: '#191c1e' }}
                  />
                </PieChart>
              )}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-2xl font-black text-primary leading-none">82.4</span>
                <span className="text-[9px] font-bold text-outline uppercase tracking-tighter">Avg Index</span>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs bg-surface-container-low/50 p-2.5 rounded-lg ring-1 ring-outline-variant/15">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-primary"></div>
                  <span className="font-medium text-on-surface-variant">Excessive Speeding</span>
                </div>
                <span className="font-bold text-primary">60%</span>
              </div>
              <div className="flex items-center justify-between text-xs bg-surface-container-low/50 p-2.5 rounded-lg ring-1 ring-outline-variant/15">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-error"></div>
                  <span className="font-medium text-on-surface-variant">Distracted Driving</span>
                </div>
                <span className="font-bold text-primary">35%</span>
              </div>
              <div className="flex items-center justify-between text-xs bg-surface-container-low/50 p-2.5 rounded-lg ring-1 ring-outline-variant/15">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-secondary"></div>
                  <span className="font-medium text-on-surface-variant">Tailgating</span>
                </div>
                <span className="font-bold text-primary">15%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* High-Risk Drivers & Live Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* High-Risk Drivers */}
        <div className="lg:col-span-4 bg-surface-container-lowest rounded-xl ring-1 ring-outline-variant/15 shadow-sm overflow-hidden flex flex-col">
          <div className="px-6 py-4 border-b border-surface-container-high flex justify-between items-center bg-surface-container-low/30">
            <h3 className="text-sm font-bold text-primary uppercase tracking-wider">High-Risk Drivers</h3>
            <span className="text-[10px] font-bold text-error bg-error-container px-2 py-0.5 rounded uppercase">Action Req</span>
          </div>
          <div className="divide-y divide-surface-container-high flex-1">
            {[
              { name: "Marcus Henderson", id: "DRV-8842", score: 92, trend: "up", img: "https://picsum.photos/seed/marcus/100/100" },
              { name: "Sarah Jenkins", id: "DRV-1093", score: 88, trend: "up", img: "https://picsum.photos/seed/sarah/100/100" },
              { name: "Robert Chen", id: "DRV-5521", score: 85, trend: "down", img: "https://picsum.photos/seed/robert/100/100" },
              { name: "Emily Davis", id: "DRV-3304", score: 81, trend: "up", img: "https://picsum.photos/seed/emily/100/100" },
            ].map((driver, i) => (
              <div key={i} className="p-4 hover:bg-surface-container-low transition-colors flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <img src={driver.img} alt={driver.name} className="w-10 h-10 rounded-full object-cover ring-2 ring-surface-container-high" referrerPolicy="no-referrer" />
                  <div>
                    <p className="text-sm font-bold text-primary">{driver.name}</p>
                    <p className="text-[10px] font-medium text-secondary uppercase tracking-wider">{driver.id}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-black text-error">{driver.score}</p>
                  <p className="text-[9px] font-bold text-outline uppercase tracking-widest">Score</p>
                </div>
              </div>
            ))}
          </div>
          <div className="p-4 border-t border-surface-container-high bg-surface-container-low/30">
            <button className="w-full py-2 text-xs font-bold text-primary hover:bg-surface-container-low rounded transition-colors">View All Drivers</button>
          </div>
        </div>

        {/* Live Incident Feed */}
        <div className="lg:col-span-8 bg-surface-container-lowest rounded-xl ring-1 ring-outline-variant/15 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-container-high flex justify-between items-center bg-surface-container-low/30">
            <h3 className="text-sm font-bold text-primary uppercase tracking-wider">Live Incident Feed</h3>
            <span className="text-[10px] font-bold text-outline uppercase">Real-time update active</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-surface-container-low border-b border-surface-container-high">
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Timestamp</th>
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Asset ID</th>
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Severity</th>
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Violation Type</th>
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Geo-Location</th>
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary text-center">Response</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-container-high">
                <tr className="hover:bg-surface-container-low transition-colors cursor-pointer" onClick={() => onNavigate("incident")}>
                  <td className="px-6 py-4 text-xs font-medium text-on-surface-variant">Oct 24, 14:22:10</td>
                  <td className="px-6 py-4 text-xs font-bold text-primary">TX-4029-A</td>
                  <td className="px-6 py-4">
                    <span className="bg-error-container text-on-error-container px-2 py-0.5 rounded text-[9px] font-bold uppercase">Critical</span>
                  </td>
                  <td className="px-6 py-4 text-xs font-medium text-on-surface-variant">Hard Impact Detected</td>
                  <td className="px-6 py-4 text-xs text-secondary">Austin, TX (30.26, -97.74)</td>
                  <td className="px-6 py-4">
                    <div className="flex justify-center gap-2">
                      <button className="bg-primary text-on-primary text-[9px] font-bold uppercase px-3 py-1.5 rounded hover:opacity-90 shadow-sm transition-opacity">Review</button>
                      <button className="ring-1 ring-outline-variant/15 text-primary text-[9px] font-bold uppercase px-3 py-1.5 rounded hover:bg-surface-container-low transition-colors bg-surface-container-lowest">Log</button>
                    </div>
                  </td>
                </tr>
                <tr className="hover:bg-surface-container-low transition-colors">
                  <td className="px-6 py-4 text-xs font-medium text-on-surface-variant">Oct 24, 13:58:45</td>
                  <td className="px-6 py-4 text-xs font-bold text-primary">NY-8821-C</td>
                  <td className="px-6 py-4">
                    <span className="bg-amber-100 text-amber-700 px-2 py-0.5 rounded text-[9px] font-bold uppercase">Moderate</span>
                  </td>
                  <td className="px-6 py-4 text-xs font-medium text-on-surface-variant">Lane Departure Warning</td>
                  <td className="px-6 py-4 text-xs text-secondary">Buffalo, NY (42.88, -78.87)</td>
                  <td className="px-6 py-4">
                    <div className="flex justify-center gap-2">
                      <button className="bg-primary text-on-primary text-[9px] font-bold uppercase px-3 py-1.5 rounded hover:opacity-90 shadow-sm transition-opacity">Review</button>
                      <button className="ring-1 ring-outline-variant/15 text-primary text-[9px] font-bold uppercase px-3 py-1.5 rounded hover:bg-surface-container-low transition-colors bg-surface-container-lowest">Log</button>
                    </div>
                  </td>
                </tr>
                <tr className="hover:bg-surface-container-low transition-colors">
                  <td className="px-6 py-4 text-xs font-medium text-on-surface-variant">Oct 24, 13:45:12</td>
                  <td className="px-6 py-4 text-xs font-bold text-primary">CA-1002-K</td>
                  <td className="px-6 py-4">
                    <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-[9px] font-bold uppercase">Advisory</span>
                  </td>
                  <td className="px-6 py-4 text-xs font-medium text-on-surface-variant">Speeding &gt; 15mph Limit</td>
                  <td className="px-6 py-4 text-xs text-secondary">San Jose, CA (37.33, -121.88)</td>
                  <td className="px-6 py-4">
                    <div className="flex justify-center gap-2">
                      <button className="bg-primary text-on-primary text-[9px] font-bold uppercase px-3 py-1.5 rounded hover:opacity-90 shadow-sm transition-opacity">Review</button>
                      <button className="ring-1 ring-outline-variant/15 text-primary text-[9px] font-bold uppercase px-3 py-1.5 rounded hover:bg-surface-container-low transition-colors bg-surface-container-lowest">Log</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
