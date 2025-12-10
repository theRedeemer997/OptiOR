"use client";

/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect, useState } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { Plus, Calendar as CalendarIcon, Activity, Clock } from 'lucide-react';
import { format, isSameDay } from 'date-fns';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
    PieChart, Pie, Cell
} from 'recharts';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';

import { api } from '@/services/api';
import { SurgeryCase } from '@/components/types';
import { ScheduleModal } from './ScheduleModal';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

export default function Dashboard() {
    const [mounted, setMounted] = useState(false);
    const [cases, setCases] = useState<SurgeryCase[]>([]);
    const [stats, setStats] = useState({ total_cases: 0, avg_duration: 0, utilization: 'Low' });
    const [chartsData, setChartsData] = useState<any>({ service_counts: {}, or_suite_counts: {} });
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedDate, setSelectedDate] = useState<Date>(new Date());
    const [editCase, setEditCase] = useState<SurgeryCase | null>(null);
    const [filterPeriod, setFilterPeriod] = useState('all');

    const fetchData = async () => {
        try {
            const [casesData, statsData, charts] = await Promise.all([
                api.getCases(),
                api.getAnalyticsStatus(filterPeriod),
                api.getAnalyticsCharts(filterPeriod)
            ]);
            setCases(casesData);
            setStats(statsData);
            setChartsData(charts);
        } catch (error) {
            console.error("Failed to fetch data:", error);
        }
    };

    useEffect(() => {
        setMounted(true);
        fetchData();
    }, [filterPeriod]); // Re-fetch when filter changes

    if (!mounted) return null;

    const handleDateClick = (arg: { date: Date }) => {
        setSelectedDate(arg.date);
        setEditCase(null); // Create mode
        setIsModalOpen(true);
    };

    const handleEventClick = (info: any) => {
        const clickedCase = cases.find(c => c.id.toString() === info.event.id);
        if (clickedCase) {
            setEditCase(clickedCase);
            setSelectedDate(new Date(clickedCase.start));
            setIsModalOpen(true);
        }
    };

    // Transform Data for Recharts
    const serviceData = Object.entries(chartsData.service_counts || {}).map(([name, value]) => ({ name, value }));
    const orData = Object.entries(chartsData.or_suite_counts || {}).map(([name, value]) => ({ name: `OR ${name}`, value }));
    const doctorData = Object.entries(chartsData.doctor_counts || {}).map(([name, value]) => ({ name, value }));

    return (
        <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Opti OR</h1>
                    <p className="text-muted-foreground">Manage OR schedules and optimize utilization.</p>
                </div>
                <div className="flex items-center gap-2">
                    <Select value={filterPeriod} onValueChange={setFilterPeriod}>
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder="Period" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="day">Today</SelectItem>
                            <SelectItem value="month">This Month</SelectItem>
                            <SelectItem value="year">This Year</SelectItem>
                            <SelectItem value="all">All Time</SelectItem>
                        </SelectContent>
                    </Select>

                    <Button onClick={() => { setSelectedDate(new Date()); setEditCase(null); setIsModalOpen(true); }}>
                        <Plus className="mr-2 h-4 w-4" /> New Schedule
                    </Button>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid gap-4 md:grid-cols-3">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Scheduled</CardTitle>
                        <CalendarIcon className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.total_cases}</div>
                        <p className="text-xs text-muted-foreground">Surgeries in period ({filterPeriod})</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Avg Duration</CardTitle>
                        <Clock className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.avg_duration} min</div>
                        <p className="text-xs text-muted-foreground">Average operational time</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Utilization Status</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.utilization}</div>
                        <p className="text-xs text-muted-foreground">Based on current load</p>
                    </CardContent>
                </Card>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <Card>
                    <CardHeader>
                        <CardTitle>Case Distribution by Specialty</CardTitle>
                    </CardHeader>
                    <CardContent className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={serviceData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    fill="#8884d8"
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {serviceData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Cases by OR Suite</CardTitle>
                    </CardHeader>
                    <CardContent className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={orData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="name" />
                                <YAxis />
                                <Tooltip />
                                <Bar dataKey="value" fill="#82ca9d" name="Surgeries" />
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                <Card className="col-span-1 md:col-span-2 lg:col-span-1">
                    <CardHeader>
                        <CardTitle>Top Surgeons</CardTitle>
                    </CardHeader>
                    <CardContent className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={doctorData} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis type="number" />
                                <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 12 }} />
                                <Tooltip />
                                <Bar dataKey="value" fill="#8884d8" name="Surgeries" />
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Main Calendar - Span 3 cols */}
                <div className="lg:col-span-3">
                    <Card className="h-full">
                        <CardContent className="p-4">
                            <FullCalendar
                                plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
                                initialView="dayGridMonth"
                                headerToolbar={{
                                    left: 'prev,next today',
                                    center: 'title',
                                    right: 'dayGridMonth,timeGridWeek,timeGridDay'
                                }}
                                events={cases}
                                dateClick={handleDateClick}
                                eventClick={handleEventClick}
                                height="auto"
                                aspectRatio={1.8}
                            />
                        </CardContent>
                    </Card>
                </div>

                {/* Today's List - Span 1 col */}
                <div className="space-y-4">
                    <Card className="h-full">
                        <CardHeader>
                            <CardTitle>Upcoming Today</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {cases.filter(c => isSameDay(new Date(c.start), new Date())).length === 0 && (
                                    <p className="text-sm text-muted-foreground text-center py-4">
                                        No surgeries today.
                                    </p>
                                )}
                                {cases
                                    .filter(c => isSameDay(new Date(c.start), new Date()))
                                    .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime())
                                    .map((c) => (
                                        <div key={c.id} className="flex items-center justify-between p-2 border rounded-lg hover:bg-slate-50 transition-colors cursor-pointer" onClick={() => {
                                            setEditCase(c);
                                            setSelectedDate(new Date(c.start));
                                            setIsModalOpen(true);
                                        }}>
                                            <div className="space-y-1">
                                                <p className="text-sm font-medium leading-none">{c.extendedProps.patient_name}</p>
                                                <div className="flex items-center text-xs text-muted-foreground">
                                                    <span className="truncate max-w-[120px]">{c.extendedProps.service}</span>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-sm font-bold">{format(new Date(c.start), 'h:mm a')}</p>
                                                <p className="text-xs text-muted-foreground">OR {c.extendedProps.or_suite}</p>
                                            </div>
                                        </div>
                                    ))}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>

            <ScheduleModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                selectedDate={selectedDate}
                onSuccess={fetchData}
                existingAndAllCases={cases}
                editCase={editCase}
            />
        </div>
    );
}
