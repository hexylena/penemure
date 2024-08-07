package models

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"text/template"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	// "github.com/go-chi/render"
	"net/http"

	pma "github.com/hexylena/pm/adapter"
	pmc "github.com/hexylena/pm/config"
	pml "github.com/hexylena/pm/log"
	pmd "github.com/hexylena/pm/md"
	pmm "github.com/hexylena/pm/models"
)

var gn *pmm.GlobalNotes
var ga *pma.TaskAdapter
var config *pmc.HxpmConfig
var logger = pml.L("server")

func Serve(_gn *pmm.GlobalNotes, _ga *pma.TaskAdapter, _config *pmc.HxpmConfig) {
	config = _config
	ga = _ga
	gn = _gn

	r := chi.NewRouter()
	r.Mount(config.ExportPrefix, MainRoutes(gn, config))

	if config.ExportPrefix != "/" {
		r.Get("/", func(w http.ResponseWriter, r *http.Request) {
			http.Redirect(w, r, config.ExportPrefix, http.StatusFound)
		})
	}
	r.NotFound(serve_404)

	logger.Info("Starting server", "addr", config.ServerBindAddr)
	err := http.ListenAndServe(config.ServerBindAddr, r)
	if err != nil {
		logger.Error("Error", "err", err)
	}
}

func MainRoutes(gn *pmm.GlobalNotes, config *pmc.HxpmConfig) chi.Router {
	r := chi.NewRouter()

	// A good base middleware stack
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	// Set a timeout value on the request context (ctx), that will signal
	// through ctx.Done() that the request has timed out and further
	// processing should be stopped.
	r.Use(middleware.Timeout(60 * time.Second))

	r.Get("/", func(w http.ResponseWriter, r *http.Request) {
		server_fn("list", w, r)
	})
	r.Get("/manifest.json", serve_manifest_json)
	r.Get("/index.html", func(w http.ResponseWriter, r *http.Request) {
		server_fn("list", w, r)
	})
	r.Get("/search.html", func(w http.ResponseWriter, r *http.Request) {
		server_fn("search", w, r)
	})
	r.Get("/time", func(w http.ResponseWriter, r *http.Request) {
		server_fn("time", w, r)
	})
	r.Post("/time", func(w http.ResponseWriter, r *http.Request) {
		// handle form
		err := r.ParseForm()
		if err != nil {
			logger.Error("Unparseable data", "err", err)
		}
		formData := r.Form

		var note *pmm.Note
		if ok := formData["note_id"]; len(ok) > 0 {
			partial := pmm.PartialNoteId(ok[0])
			note_id, err := gn.GetIdByPartial(partial)
			if err != nil {
				note = pmm.NewNote()
				logger.Info("Could not find note", "note_id", note_id)
			} else {
				note = gn.GetNoteByID(note_id)
				logger.Info("Found note", "note", note)
			}
		} else {
			note = pmm.NewNote()
			logger.Info("New note!")
		}

		if ok := formData["action"]; len(ok) > 0 {
			switch formData["action"][0] {
			case "start":
				logger.Info("Starting task")
				note.AddMeta("time", "start_time", strconv.FormatInt(time.Now().Unix(), 10))
			case "stop":
				logger.Info("Stopping task")
				note.AddMeta("time", "end_time", strconv.FormatInt(time.Now().Unix(), 10))
			case "notes":
				text := formData["notes"][0]
				note.Blocks = pmd.MdToBlocks([]byte(text))
			}
		}

		if ok := formData["project_id"]; len(ok) > 0 {
			project_ids := strings.Split(formData["project_id"][0], ",")
			note.SetParentsFromIds(project_ids)
		}

		if ok := formData["name"]; len(ok) > 0 {
			name := formData["name"][0]
			note.Title = name
		}

		if ok := formData["tags"]; len(ok) > 0 {
			tags := strings.Split(formData["tags"][0][1:], ",")
			for _, tag := range tags {
				note.AddTag(tag)
			}
		}

		// Update where relevant
		note.Type = "log"

		fmt.Println("form", formData, "note", note)

		gn.RegisterNote(note)
		(*ga).SaveNotes(*gn)

		// process form data
		server_fn("time", w, r)
	})
	// r.Route("/notes", func(r chi.Router) {
	// 	// r.With(paginate).Get("/", listArticles)                           // GET /notes
	// 	// r.Get("/", gn.serve_listArticles)                           // GET /notes
	// 	// r.Get("/search", gn.serve_searchArticles)                                  // GET /notes/search
	r.Get("/{articleSlug:[a-f0-9-]+}.html", serve_getArticleBySlug) // GET /notes/<uuid>
	// })

	r.NotFound(serve_404)

	// Otherwise serve things directly from templates dir.
	workDir, _ := os.Getwd()
	filesDir := http.Dir(filepath.Join(workDir, "templates/assets/"))
	FileServer(r, "/assets", filesDir)
	return r
}

func get_template(templateName string) *template.Template {
	tmpl, err := template.New("").ParseFiles(fmt.Sprintf("templates/%s.html", templateName), "templates/base.html")
	if err != nil {
		logger.Error("Error", "err", err)
	}
	return tmpl
}

type templateContext struct {
	Gn     *pmm.GlobalNotes
	Config *pmc.HxpmConfig
}

func serve_404(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusNotFound)
	server_fn("404", w, r)
}

func server_fn(fn string, w http.ResponseWriter, r *http.Request) {
	tmpl := get_template(fn)
	err := tmpl.ExecuteTemplate(w, "base", templateContext{gn, config})
	if err != nil {
		logger.Error("Error", "err", err)
	}
}

func Manifest(config pmc.HxpmConfig) []byte {
	icon := map[string]string{
		"src":   config.ExportPrefix + "assets/favicon@256.png",
		"type":  "image/png",
		"sizes": "256x256",
	}
	data := map[string]interface{}{
		"background_color": "#ffffff",
		"name":             config.Title,
		"description":      config.About,
		"display":          "standalone",
		"scope":            config.ExportPrefix, // TODO: make this configurable
		"icons":            []map[string]string{icon},
		"start_url":        config.ExportPrefix, // TODO:
		"theme_color":      "#CE3518",
	}
	ret, err := json.Marshal(data)
	if err != nil {
		logger.Error("Error", "err", err)
	}
	return ret
}

func serve_manifest_json(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(config.Manifest())
}

var ErrNotFound = &ErrResponse{HTTPStatusCode: 404, StatusText: "Resource not found."}

func serve_getArticleBySlug(w http.ResponseWriter, r *http.Request) {
	if pni := chi.URLParam(r, "articleSlug"); pni != "" {
		partial := pmm.PartialNoteId(pni)
		note_id, err := gn.GetIdByPartial(partial)
		if err != nil {
			serve_404(w, r)
			return
		}
		note := gn.GetNoteByID(note_id)
		note.Export(gn, w, config)
	} else {
		serve_404(w, r)
		return
	}
}

// FileServer conveniently sets up a http.FileServer handler to serve
// static files from a http.FileSystem.
func FileServer(r chi.Router, path string, root http.FileSystem) {
	if strings.ContainsAny(path, "{}*") {
		panic("FileServer does not permit any URL parameters.")
	}

	if path != "/" && path[len(path)-1] != '/' {
		r.Get(path, http.RedirectHandler(path+"/", http.StatusFound).ServeHTTP)
		path += "/"
	}
	path += "*"

	r.Get(path, func(w http.ResponseWriter, r *http.Request) {
		rctx := chi.RouteContext(r.Context())
		pathPrefix := strings.TrimSuffix(rctx.RoutePattern(), "/*")
		fs := http.StripPrefix(pathPrefix, http.FileServer(root))

		w.Header().Set("Cache-Control", "public, max-age=86400") // Set cache control header to allow caching for 24 hours
		fs.ServeHTTP(w, r)
	})
}
