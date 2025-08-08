import { Component, Input, signal } from '@angular/core';
import { CdkCopyToClipboard } from '@angular/cdk/clipboard';
import { MatIcon } from '@angular/material/icon';

@Component({
  selector: 'app-copy-button',
  standalone: true,
  imports: [CdkCopyToClipboard, MatIcon],
  templateUrl: './copy-button.component.html',
  styleUrls: ['./copy-button.component.scss'],
})
export class CopyButtonComponent {
  @Input() copyText: string = '';
  copied = signal(false);

  onCopy(): void {
    this.copied.set(true);
    setTimeout(() => this.copied.set(false), 1600);
  }
}
