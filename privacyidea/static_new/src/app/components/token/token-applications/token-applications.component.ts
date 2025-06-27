import { Component } from '@angular/core';
import { TokenApplicationsSshComponent } from './token-applications-ssh/token-applications-ssh.component';
import { TokenApplicationsOfflineComponent } from './token-applications-offline/token-applications-offline.component';
import { MatSelectModule } from '@angular/material/select';
import { MachineService } from '../../../services/machine/machine.service';

import { ContentService } from '../../../services/content/content.service';

@Component({
  selector: 'app-token-applications',
  standalone: true,
  imports: [
    TokenApplicationsSshComponent,
    TokenApplicationsOfflineComponent,
    MatSelectModule,
  ],
  templateUrl: './token-applications.component.html',
  styleUrls: ['./token-applications.component.scss'],
})
export class TokenApplicationsComponent {
  selectedApplicationType = this.machineService.selectedApplicationType;
  selectedContent = this.contentService.selectedContent;

  constructor(
    private machineService: MachineService,
    private contentService: ContentService,
  ) {}
}
