// Package server provides functionality for the server.
package server

import (
	"encoding/json"
	"fmt"
	"strings"
	"text/template"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"tailscale.com/tsnet"

	// "github.com/go-chi/render"
	"net/http"

	"embed"

	pma "github.com/hexylena/pm/adapter"
	pmc "github.com/hexylena/pm/config"
	pml "github.com/hexylena/pm/log"
	pmm "github.com/hexylena/pm/models"
)

var gn *pmm.GlobalNotes
var ga *pma.TaskAdapter
var config *pmc.HxpmConfig
var logger = pml.L("server")
var templateFS *embed.FS

type templateContext struct {
	Gn      *pmm.GlobalNotes
	Config  *pmc.HxpmConfig
	Context map[string]string
	Note    *pmm.Note
}

func (tc templateContext) AddContext(key, value string) {
	if tc.Context == nil {
		tc.Context = make(map[string]string)
	}
	tc.Context[key] = value
}

func Serve(_gn *pmm.GlobalNotes, _ga *pma.TaskAdapter, _config *pmc.HxpmConfig, _templates *embed.FS) {
	config = _config
	config.SetServing(true)
	ga = _ga
	gn = _gn
	templateFS = _templates

	r := chi.NewRouter()
	r.Mount(config.ExportPrefix, MainRoutes())

	if config.ServerBindTailscale {
		serve_tsnet(r)
	} else {
		serve_http(r)
	}
}

func serve_http(r *chi.Mux) {
	bind := fmt.Sprintf("%s:%s", config.ServerBindHost, config.ServerBindPort)
	logger.Info("Starting server", "addr", bind)
	err := http.ListenAndServe(bind, r)
	if err != nil {
		logger.Error("Error", "err", err)
	}
}

func serve_tsnet(r *chi.Mux) {
	s := tsnet.Server{Hostname: "hxpm"}
	defer s.Close()

	// Have the tsnet server listen on :8080
	ln, err := s.Listen("tcp", ":"+config.ServerBindPort)
	if err != nil {
		logger.Error("Error", "err", err)
	}
	defer ln.Close()

	err = http.Serve(ln, r)
	if err != nil {
		logger.Error("Error", "err", err)
	}

}

func urlToContext(tc *templateContext, r *http.Request) {
	note_id := r.URL.Query().Get("id")
	if note_id == "" {
		tc.AddContext("error", "No note id provided")
	} else {
		partial := pmm.PartialNoteId(note_id)
		note_id, err := gn.GetIdByPartial(partial)
		if err != nil {
			tc.AddContext("error", fmt.Sprintf("%s", err))
		}
		note := gn.GetNoteByID(note_id)
		tc.Note = note
	}
}

func MainRoutes() chi.Router {
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
	tc := templateContext{Gn: gn, Config: config, Context: map[string]string{}}

	r.Get("/", func(w http.ResponseWriter, r *http.Request) {
		tc.AddContext("id", "00000000-0000-0000-0000-000000000000")
		server_fn("list", w, r, &tc)
	})
	r.Get("/manifest.json", serve_manifest_json)
	r.Get("/index.html", func(w http.ResponseWriter, r *http.Request) {
		tc.AddContext("id", "00000000-0000-0000-0000-000000000000")
		server_fn("list", w, r, &tc)
	})
	r.Get("/search.html", func(w http.ResponseWriter, r *http.Request) {
		server_fn("search", w, r, &tc)
	})
	r.Get("/time", func(w http.ResponseWriter, r *http.Request) {
		tc.Note = gn.GetOpenLog()
		server_fn("time", w, r, &tc)
	})
	r.Post("/time", func(w http.ResponseWriter, r *http.Request) {
		// handle form
		err := r.ParseForm()
		if err != nil {
			logger.Error("Unparseable data", "err", err)
			tc.AddContext("error", fmt.Sprintf("Unparseable data, %s", err))
		} else {
			formData := r.Form
			processTimeSubmission(formData)
		}

		tc.Note = gn.GetOpenLog()

		// process form data
		server_fn("time", w, r, &tc)
	})

	r.Get("/new", func(w http.ResponseWriter, r *http.Request) {
		urlToContext(&tc, r)
		server_fn("new", w, r, &tc)
	})
	r.Post("/new", func(w http.ResponseWriter, r *http.Request) {
		urlToContext(&tc, r)
		err := r.ParseForm()
		if err != nil {
			logger.Error("Unparseable data", "err", err)
			tc.AddContext("error", fmt.Sprintf("Unparseable data, %s", err))
		} else {
			formData := r.Form
			note := processNoteSubmission(formData)
			tc.AddContext("success", fmt.Sprintf(`Saved new note as <a href="%s.html">%s</a>`, note.NoteId, note.Title))
		}

		// process form data
		server_fn("new", w, r, &tc)
	})

	r.Get("/edit", func(w http.ResponseWriter, r *http.Request) {
		urlToContext(&tc, r)
		server_fn("edit", w, r, &tc)
	})
	r.Post("/edit", func(w http.ResponseWriter, r *http.Request) {
		err := r.ParseForm()
		if err != nil {
			logger.Error("Unparseable data", "err", err)
			tc.AddContext("error", fmt.Sprintf("Unparseable data, %s", err))
		} else {
			formData := r.Form
			note := processNoteSubmission(formData)
			tc.AddContext("success", fmt.Sprintf(`Saved note <a href="%s.html">%s</a>`, note.NoteId, note.Title))
		}
		urlToContext(&tc, r)

		// process form data
		server_fn("edit", w, r, &tc)
	})

	// r.Route("/notes", func(r chi.Router) {
	// 	// r.With(paginate).Get("/", listArticles)                           // GET /notes
	// 	// r.Get("/", gn.serve_listArticles)                           // GET /notes
	// 	// r.Get("/search", gn.serve_searchArticles)                                  // GET /notes/search
	r.Get("/{articleSlug:[a-f0-9-]+}.html", serve_getArticleBySlug) // GET /notes/<uuid>
	// })

	r.NotFound(serve_404)

	// Otherwise serve things directly from templates dir.
	// workDir, _ := os.Getwd()
	// filesDir := http.Dir(filepath.Join(workDir, "templates/assets/"))
	// fmt.Println(filesDir)
	httpfs := http.FS(templateFS)
	FileServer(r, "/assets", config.ExportPrefix, httpfs)

	if config.ExportPrefix != "/" {
		r.Get("/", func(w http.ResponseWriter, r *http.Request) {
			http.Redirect(w, r, config.ExportPrefix + "index.html", http.StatusFound)
		})
	}
	r.NotFound(serve_404)

	return r
}

func get_template(templateName string) *template.Template {
	tmpl, err := template.New("").ParseFS(templateFS, fmt.Sprintf("templates/%s.html", templateName), "templates/base.html")
	if err != nil {
		logger.Error("Error", "err", err)
	}
	return tmpl
}

func serve_404(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusNotFound)
	tc := templateContext{Gn: gn, Config: config, Context: map[string]string{}}
	server_fn("404", w, r, &tc)
}

func server_fn(fn string, w http.ResponseWriter, r *http.Request, tc *templateContext) {
	tmpl := get_template(fn)
	err := tmpl.ExecuteTemplate(w, "base", tc)
	if err != nil {
		logger.Error("Error", "err", err)
	}
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
		note.Export(gn, w, config, templateFS)
	} else {
		serve_404(w, r)
		return
	}
}

// FileServer conveniently sets up a http.FileServer handler to serve
// static files from a http.FileSystem.
func FileServer(r chi.Router, path string, prefix string, root http.FileSystem) {
	if strings.ContainsAny(path, "{}*") {
		panic("FileServer does not permit any URL parameters.")
	}

	if path != "/" && path[len(path)-1] != '/' {
		r.Get(path, http.RedirectHandler(path+"/", http.StatusFound).ServeHTTP)
		path += "/"
	}
	path += "*"

	r.Get(path, func(w http.ResponseWriter, r *http.Request) {
		// rctx := chi.RouteContext(r.Context())
		// pathPrefix := strings.TrimSuffix(rctx.RoutePattern(), "/*")
		// fmt.Println(pathPrefix)
		fs := http.StripPrefix(prefix, http.FileServer(root))

		// we don't strip /assets because that's actually our folder name and
		// where we want to serve it.
		// fs := http.FileServer(root)

		w.Header().Set("Cache-Control", "public, max-age=86400") // Set cache control header to allow caching for 24 hours
		fs.ServeHTTP(w, r)
	})
}
