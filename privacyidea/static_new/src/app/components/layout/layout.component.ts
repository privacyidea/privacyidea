import { NgClass } from "@angular/common";
import { Component, inject, signal } from "@angular/core";
import { RouterOutlet } from "@angular/router";
import { AuthService, AuthServiceInterface } from "../../services/auth/auth.service";
import { LoadingService, LoadingServiceInterface } from "../../services/loading/loading-service";
import { HeaderComponent } from "./header/header.component";
import { HeaderSelfServiceComponent } from "./header/header.serlf-service.component";
import { MatProgressBar } from "@angular/material/progress-bar";

@Component({
  selector: "layout",
  templateUrl: "layout.component.html",
  standalone: true,
  imports: [
    RouterOutlet,
    HeaderComponent,
    HeaderSelfServiceComponent,
    NgClass,
    MatProgressBar
  ],
  styleUrl: "./layout.component.scss"
})
export class LayoutComponent {
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly loadingService: LoadingServiceInterface =
    inject(LoadingService);
  showProgressBar = signal(false);
  loadingUrls = signal<{ key: string; url: string }[]>([]);

  ngOnInit(): void {
    this.loadingService.addListener("layout", () => {
      this.showProgressBar.set(this.loadingService.isLoading());
      this.loadingUrls.set(this.loadingService.getLoadingUrls());
    });
  }

  ngOnDestroy(): void {
    this.loadingService.removeListener("layout");
  }
}
