import { Component, Input, signal, WritableSignal } from '@angular/core';
import { TokenApplicationsSsh } from './token-applications-ssh/token-applications-ssh';
import { TokenApplicationsOffline } from './token-applications-offline/token-applications-offline';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-token-applications',
  standalone: true,
  imports: [
    TokenApplicationsSsh,
    TokenApplicationsOffline,
    MatSelectModule,
  ],
  templateUrl: './token-applications.html',
  styleUrls: ['./token-applications.scss'],
})
export class TokenApplications {
  @Input({ required: true }) tokenSerial!: WritableSignal<string>;
  @Input({ required: true }) selectedContent!: WritableSignal<string>;
  selectedApplicationType = signal('ssh');


}
