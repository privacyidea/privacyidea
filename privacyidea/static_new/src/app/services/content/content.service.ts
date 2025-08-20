import { computed, inject, Injectable, Signal, signal, WritableSignal } from "@angular/core";
import { NavigationEnd, Router } from "@angular/router";
import { filter, map, pairwise, startWith } from "rxjs";
import { toSignal } from "@angular/core/rxjs-interop";
import { ROUTE_PATHS } from "../../app.routes";

export interface ContentServiceInterface {
  router: Router;
  routeUrl: () => string;
  previousUrl: Signal<string>;
  isProgrammaticTabChange: WritableSignal<boolean>;
  tokenSerial: WritableSignal<string>;
  containerSerial: WritableSignal<string>;
  tokenSelected: (serial: string) => void;
  containerSelected: (containerSerial: string) => void;
}

@Injectable({ providedIn: "root" })
export class ContentService {
  readonly routeUrl = computed(() => this._urlPair()[1]);
  readonly previousUrl = computed(() => this._urlPair()[0]);
  router = inject(Router);
  private readonly _urlPair = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map((e) => e.urlAfterRedirects),
      startWith(this.router.url),
      pairwise()
    ),
    { initialValue: [this.router.url, this.router.url] as const }
  );
  isProgrammaticTabChange = signal(false);
  tokenSerial = signal("");
  containerSerial = signal("");

  tokenSelected(serial: string) {
    if (this.routeUrl().includes("containers")) {
      this.isProgrammaticTabChange.set(true);
    }
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_DETAILS + serial);
    this.tokenSerial.set(serial);
  }

  containerSelected(containerSerial: string) {
    if (!this.routeUrl().includes("containers")) {
      this.isProgrammaticTabChange.set(true);
    }
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + containerSerial);
    this.containerSerial.set(containerSerial);
  }
}
