import { Component } from '@angular/core';
import { TokenApplicationsSsh } from './token-applications-ssh/token-applications-ssh';

@Component({
  selector: 'app-token-applications',
  standalone: true,
  imports: [TokenApplicationsSsh],
  templateUrl: './token-applications.html',
  styleUrls: ['./token-applications.scss'],
})
export class TokenApplications {}
