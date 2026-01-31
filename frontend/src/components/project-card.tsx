import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Project } from "@/lib/api";
import { CalendarDays, Image as ImageIcon } from "lucide-react";

export function ProjectCard({ project }: { project: Project }) {
  const date = new Date(project.created_at).toLocaleDateString();

  return (
    <Link href={`/project/${project.id}`}>
      <Card className="hover:bg-accent/50 transition-colors cursor-pointer h-full flex flex-col">
        <CardHeader>
          <CardTitle className="line-clamp-1">{project.name}</CardTitle>
          <CardDescription>ID: {project.id}</CardDescription>
        </CardHeader>
        <CardContent className="mt-auto flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <CalendarDays className="h-4 w-4" />
            <span>{date}</span>
          </div>
          <div className="flex items-center gap-1">
            <ImageIcon className="h-4 w-4" />
            <span>{project.image_count}</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
