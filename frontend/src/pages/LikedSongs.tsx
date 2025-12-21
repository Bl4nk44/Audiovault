import { Heart, Play } from "lucide-react";
import { motion } from "framer-motion";

export default function LikedSongs() {
  return (
    <div className="space-y-8">
      <div className="flex items-end gap-6">
        <div className="w-52 h-52 bg-linear-to-br from-purple-700 to-blue-900 rounded-2xl shadow-2xl flex items-center justify-center relative overflow-hidden group">
          <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <Play size={48} className="text-white fill-white" />
          </div>
          <Heart size={80} className="text-white fill-white drop-shadow-lg" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-bold uppercase tracking-wider text-foreground mb-2">
            Playlist
          </p>
          <h1 className="text-7xl font-black text-foreground mb-6 tracking-tight drop-shadow-xl">
            Liked Songs
          </h1>
          <div className="flex items-center gap-2 text-sm text-muted-foreground font-medium">
            <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-bold text-xs">
              M
            </div>
            <span className="text-foreground hover:underline cursor-pointer">
              Mati
            </span>
            <span>•</span>
            <span>123 songs</span>
          </div>
        </div>
      </div>

      <div className="bg-card/30 backdrop-blur-xl rounded-3xl border border-border p-6 min-h-[400px]">
        <div className="flex items-center justify-between mb-6 px-4 text-sm text-muted-foreground font-medium border-b border-border pb-2">
          <div className="flex items-center gap-4 w-1/2">
            <span>#</span>
            <span>Title</span>
          </div>
          <div className="w-1/4">Album</div>
          <div className="w-1/4 text-right pr-8">Date Added</div>
          <div className="w-12 text-center">Duration</div>
        </div>

        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-center justify-between p-3 rounded-xl hover:bg-accent/50 group transition-colors cursor-pointer border border-transparent hover:border-border"
            >
              <div className="flex items-center gap-4 w-1/2">
                <span className="text-muted-foreground w-4 text-center group-hover:hidden">
                  {i}
                </span>
                <Play
                  size={16}
                  className="text-foreground hidden group-hover:block w-4"
                />
                <div className="w-10 h-10 bg-secondary rounded-lg shrink-0" />
                <div>
                  <p className="font-bold text-foreground group-hover:text-primary transition-colors">
                    Song Title {i}
                  </p>
                  <p className="text-sm text-muted-foreground group-hover:text-foreground">
                    Artist Name
                  </p>
                </div>
              </div>
              <div className="w-1/4 text-muted-foreground text-sm group-hover:text-foreground transition-colors">
                Album Name
              </div>
              <div className="w-1/4 text-right pr-8 text-muted-foreground text-sm">
                2 days ago
              </div>
              <div className="w-12 text-center text-muted-foreground text-sm">
                3:45
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
