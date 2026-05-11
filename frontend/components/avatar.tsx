"use client";

interface AvatarProps {
  name: string | null;
  avatarUrl: string | null;
  size?: "sm" | "md" | "lg";
}

const sizes = {
  sm: "h-7 w-7 text-xs",
  md: "h-9 w-9 text-sm",
  lg: "h-12 w-12 text-base",
};

function getInitials(name: string | null): string {
  if (!name) return "?";
  return name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function getColor(name: string | null): string {
  const colors = [
    "bg-red-500",
    "bg-orange-500",
    "bg-amber-500",
    "bg-green-500",
    "bg-teal-500",
    "bg-blue-500",
    "bg-indigo-500",
    "bg-purple-500",
    "bg-pink-500",
  ];
  if (!name) return colors[0];
  const index = name.charCodeAt(0) % colors.length;
  return colors[index];
}

export function Avatar({ name, avatarUrl, size = "md" }: AvatarProps) {
  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt={name ?? "User avatar"}
        className={`${sizes[size]} rounded-full object-cover shrink-0`}
        referrerPolicy="no-referrer"
      />
    );
  }

  return (
    <div
      className={`${sizes[size]} ${getColor(name)} rounded-full flex items-center justify-center text-white font-medium shrink-0`}
    >
      {getInitials(name)}
    </div>
  );
}
