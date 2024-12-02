import {Component, OnInit} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatButtonModule} from '@angular/material/button';
import {VersionService} from '../../../services/version/version.service';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [
    MatIconModule,
    MatButtonModule
  ],
  templateUrl: './footer.component.html',
  styleUrl: './footer.component.css'
})
export class FooterComponent implements OnInit {
  version!: string;

  constructor(private versioningService: VersionService) {
  }

  ngOnInit(): void {
    this.version = this.versioningService.getVersion();
  }
}
