import { Component, Inject, OnInit, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBar } from '@angular/material/progress-bar';
import {
  LoadingService,
  LoadingServiceInterface,
} from '../../../services/loading/loading-service';
import {
  VersioningService,
  VersioningServiceInterface,
} from '../../../services/version/version.service';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [MatIconModule, MatButtonModule, MatProgressBar],
  templateUrl: './footer.component.html',
  styleUrl: './footer.component.scss',
})
export class FooterComponent implements OnInit {
  version!: string;
  showProgressBar = signal(false);
  loadingUrls = signal<{ key: string; url: string }[]>([]);

  constructor(
    @Inject(VersioningService)
    private readonly versioningService: VersioningServiceInterface,
    @Inject(LoadingService)
    private readonly loadingService: LoadingServiceInterface,
  ) {}

  ngOnInit(): void {
    this.version = this.versioningService.getVersion();
    this.loadingService.addListener('footer', () => {
      this.showProgressBar.set(this.loadingService.isLoading());
      this.loadingUrls.set(this.loadingService.getLoadingUrls());
    });
  }

  ngOnDestroy(): void {
    this.loadingService.removeListener('footer');
  }
}
