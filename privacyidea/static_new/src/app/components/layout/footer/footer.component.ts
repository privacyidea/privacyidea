import { Component, OnInit, signal } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { VersionService } from '../../../services/version/version.service';
import { MatProgressBar } from '@angular/material/progress-bar';
import { LoadingService } from '../../../services/loading/loading-service';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [MatIconModule, MatButtonModule, MatProgressBar],
  templateUrl: './footer.component.html',
  styleUrl: './footer.component.scss',
})
export class FooterComponent implements OnInit {
  version!: string;
  showProgressBar = signal<boolean>(false);

  constructor(
    private versioningService: VersionService,
    private loadingService: LoadingService,
  ) {}

  ngOnInit(): void {
    this.version = this.versioningService.getVersion();
    this.loadingService.addListener('footer', () => {
      this.showProgressBar.set(this.loadingService.isLoading());
    });
  }

  ngOnDestroy(): void {
    this.loadingService.removeListener('footer');
  }
}
